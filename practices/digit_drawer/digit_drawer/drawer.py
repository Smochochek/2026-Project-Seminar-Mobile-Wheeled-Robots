import math
import rclpy
from rclpy.node import Node


from geometry_msgs.msg import Twist
from turtlesim.msg import Pose as TurtlePose

from turtlesim.srv import SetPen


def wrap_to_pi(angle: float) -> float:
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))


DIGIT_PATHS = {
    0: [(0, 0, False), (1, 0, True), (1, 2, True), (0, 2, True), (0, 0, True)],
    1: [(1, 0, False), (1, 2, True)],
    2: [(0, 2, False), (1, 2, True), (1, 1, True), (0, 1, True), (0, 0, True), (1, 0, True)],
    3: [(0, 2, False), (1, 2, True), (1, 1, True), (0, 1, True), (1, 1, False), (1, 0, True), (0, 0, True)],
    4: [(0, 2, False), (0, 1, True), (1, 1, True), (1, 2, False), (1, 0, True)],
    5: [(1, 2, False), (0, 2, True), (0, 1, True), (1, 1, True), (1, 0, True), (0, 0, True)],
    6: [(1, 2, False), (0, 2, True), (0, 0, True), (1, 0, True), (1, 1, True), (0, 1, True)],
    7: [(0, 2, False), (1, 2, True), (1, 0, True)],
    8: [(0, 1, False), (0, 2, True), (1, 2, True), (1, 0, True), (0, 0, True), (0, 1, True), (1, 1, True)],
    9: [(0, 0, False), (1, 0, True), (1, 2, True), (0, 2, True), (0, 1, True), (1, 1, True)],
}


class DigitDrawer(Node):
    def __init__(self):
        super().__init__("digit_drawer")

        self.declare_parameter("turtle", "turtle3")  # имя черепахи
        self.declare_parameter("digit", 0)           # Цифра
        self.declare_parameter("offset_x", 2.0)      # Смещение цифры по х
        self.declare_parameter("offset_y", 3.0)      # Смещение цифры по у
        self.declare_parameter("scale", 1.5)         # Масштаб цифры

        self.turtle = self.get_parameter("turtle").value
        self.digit = int(self.get_parameter("digit").value)
        self.offset_x = float(self.get_parameter("offset_x").value)
        self.offset_y = float(self.get_parameter("offset_y").value)
        self.scale = float(self.get_parameter("scale").value)


        self.control_hz = 20.0
        self.dt = 1.0 / self.control_hz
        self.tol = 0.08
        self.k_lin = 2.0
        self.k_ang = 6.0
        self.max_lin = 1.5
        self.max_ang = 3.0

        self.pose = None                # текущая координата черепахи
        self.current_pen_off = None     # состояние пера


        # Подписываемся на топик координат
        self.pose_sub = self.create_subscription(
            TurtlePose, f"/{self.turtle}/pose", self.on_pose, 10
        )

        # Издатель для команд скорости
        self.cmd_pub = self.create_publisher(
            Twist, f"/{self.turtle}/cmd_vel", 10
        )

        # клиент сервиса для пера
        self.pen_client = self.create_client(
            SetPen, f"/{self.turtle}/set_pen"
        )


        raw_path = DIGIT_PATHS.get(self.digit, DIGIT_PATHS[0])
        self.waypoints = [
            (self.offset_x + lx * self.scale, self.offset_y + ly * self.scale, draw)
            for lx, ly, draw in raw_path
        ]
        self.current_idx = 0  # Индекс текущей целевой точки из списка waypoints

        # Запускаем периодический таймер, который будет вызывать функцию control_loop
        self.timer = self.create_timer(self.dt, self.control_loop)

        self.get_logger().info(
            f"Черепаха '{self.turtle}' готова рисовать цифру {self.digit}. "
            f"Всего опорных точек: {len(self.waypoints)}"
        )

    def on_pose(self, msg: TurtlePose):
        self.pose = msg

    def set_pen(self, draw: bool):
        target_off = 0 if draw else 1

        if self.current_pen_off == target_off:
            return

        # Проверяем, доступен ли сервис симулятора
        if not self.pen_client.service_is_ready():
            return

        # Формируем запрос к сервису SetPen
        req = SetPen.Request()
        req.r = 255      # Цвет линии: красный
        req.g = 255      # зеленый
        req.b = 255      # синий (255, 255, 255 = белый след)
        req.width = 3    # Толщина линии
        req.off = target_off

        # Асинхронно отправляем запрос в turtlesim
        self.pen_client.call_async(req)
        self.current_pen_off = target_off

    def control_loop(self):
        """
        Основной цикл управления. Вызывается по таймеру 20 раз в секунду.
        Вычисляет, куда нужно повернуть и с какой скоростью ехать.
        """
        # Если turtlesim еще не прислал первую позицию, ждать
        if self.pose is None:
            return

        # Если список точек закончился — цифра нарисована, глушим двигатели
        if self.current_idx >= len(self.waypoints):
            self.cmd_pub.publish(Twist())
            return

        # Берем текущую целевую точку
        target_x, target_y, should_draw = self.waypoints[self.current_idx]

        # Включаем или выключаем след пера для этого отрезка
        self.set_pen(should_draw)

        # Расстояние от черепахи до целевой точки
        dx = target_x - self.pose.x
        dy = target_y - self.pose.y
        dist = math.hypot(dx, dy)

        # Если черепаха подошла достаточно близко к точке:
        if dist < self.tol:
            self.get_logger().info(f"Точка {self.current_idx + 1}/{len(self.waypoints)} достигнута.")
            self.current_idx += 1  # Переключаемся на следующую точку
            return

        # Вычисляем угол по направлению к цели
        desired_angle = math.atan2(dy, dx)

        # Вычисляем ошибку ориентации: насколько градусов нужно повернуться
        angle_error = wrap_to_pi(desired_angle - self.pose.theta)

        # Если черепаха сильно смотрит в другую сторону
        # сбрасываем скорость вперед до минимума, чтобы она сначала повернулась
        if abs(angle_error) > 0.6:
            linear_v = 0.1
        else:
            # Пропорциональный регулятор: чем ближе к цели, тем плавнее подъезжаем
            linear_v = min(self.k_lin * dist, self.max_lin)

        # П-регулятор угловой скорости: вращаемся со скоростью, пропорциональной ошибке угла
        angular_w = clamp(self.k_ang * angle_error, -self.max_ang, self.max_ang)

        # Формируем и публикуем управляющее сообщение скорости в топик cmd_vel
        cmd = Twist()
        cmd.linear.x = float(linear_v)
        cmd.angular.z = float(angular_w)
        self.cmd_pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = DigitDrawer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()