import math
import os
from geometry_msgs.msg import TwistStamped
import matplotlib
from rclpy.node import Node
import rclpy
from rosgraph_msgs.msg import Clock
import tf2_ros

# Режим без открытия графического окна (для Linux / Docker)
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def normalize_angle(angle):
  """Приведение угла к диапазону [-pi, pi], чтобы не было разрывов при переходе через 180 градусов."""
  while angle > math.pi:
    angle -= 2.0 * math.pi
  while angle < -math.pi:
    angle += 2.0 * math.pi
  return angle


class OdometryNode(Node):

  def __init__(self):
    super().__init__('odometry_analysis')
    self.last_time = 0
    self.sim_time = 0.0
    self.v = 0.0
    self.w = 0.0

    self.not_initialized = 1
    self.cmd_x = 0.0
    self.cmd_y = 0.0
    self.cmd_yaw = 0.0
    self.start_time = 0

    # Списки историй (для 1-го графика XY)
    self.gt_x_history = []
    self.gt_y_history = []
    self.enc_x_history = []
    self.enc_y_history = []
    self.cmd_x_history = []
    self.cmd_y_history = []

    # Списки историй (для 2-го и 3-го графиков ошибок)
    self.pos_error_enc_history = []
    self.pos_error_cmd_history = []
    self.yaw_error_enc_history = []
    self.yaw_error_cmd_history = []
    self.time_history = []

    # Подписки
    self.clock_sub = self.create_subscription(
        Clock, '/clock', self.clock_timer_callback, 10
    )
    self.cmd_sub = self.create_subscription(
        TwistStamped, '/cmd_vel', self.cmd_timer_callback, 10
    )

    # Буфер и слушатель TF
    self.tf_buffer = tf2_ros.Buffer()
    self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

    # Таймер (20 Гц = каждые 0.05 с)
    self.timer = self.create_timer(0.05, self.timer_callback)

  def quaternion_to_yaw(self, x, y, z, w):
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)

  def timer_callback(self):
    current_time = self.sim_time

    # 1. Забираем координаты из TF
    try:
      # Истина (GT)
      t_gt = self.tf_buffer.lookup_transform(
          'map', 'base_link_gt', rclpy.time.Time()
      )
      gt_x = t_gt.transform.translation.x
      gt_y = t_gt.transform.translation.y
      q_gt = t_gt.transform.rotation
      gt_yaw = self.quaternion_to_yaw(q_gt.x, q_gt.y, q_gt.z, q_gt.w)

      # Колёсная одометрия (энкодеры)
      t_enc = self.tf_buffer.lookup_transform(
          'map', 'base_link', rclpy.time.Time()
      )
      enc_x = t_enc.transform.translation.x
      enc_y = t_enc.transform.translation.y
      q_enc = t_enc.transform.rotation
      enc_yaw = self.quaternion_to_yaw(q_enc.x, q_enc.y, q_enc.z, q_enc.w)

    except (
        tf2_ros.LookupException,
        tf2_ros.ConnectivityException,
        tf2_ros.ExtrapolationException,
    ):
      # В первые доли секунды ждём появления данных
      return

    # 2. Инициализация начальной точки позы GT (запускаем, когда робот поехал)
    if self.not_initialized:
      if abs(self.v) > 1e-4 or abs(self.w) > 1e-4:
        self.cmd_x = gt_x
        self.cmd_y = gt_y
        self.cmd_yaw = gt_yaw
        self.start_time = current_time
        self.last_time = current_time
        self.not_initialized = 0
        self.get_logger().info('Эксперимент начат!')
      else:
        return

    # 3. Расчёт dt
    dt = current_time - self.last_time
    if dt <= 0.0:
      return
    self.last_time = current_time

    # 4. Шаг интегрирования по командам
    self.cmd_x += self.v * math.cos(self.cmd_yaw) * dt
    self.cmd_y += self.v * math.sin(self.cmd_yaw) * dt
    self.cmd_yaw = normalize_angle(self.cmd_yaw + self.w * dt)

    # 5. Расчёт ошибок
    err_pos_enc = math.hypot(enc_x - gt_x, enc_y - gt_y)
    err_yaw_enc = abs(normalize_angle(enc_yaw - gt_yaw))

    err_pos_cmd = math.hypot(self.cmd_x - gt_x, self.cmd_y - gt_y)
    err_yaw_cmd = abs(normalize_angle(self.cmd_yaw - gt_yaw))

    # 6. Проверка времени завершения (65 секунд)
    rel_time = current_time - self.start_time
    if rel_time >= 65.0:
      self.get_logger().info('65 секунд прошло! Сохраняем графики...')
      self.save_plots()
      self.timer.cancel()
      return

    # 7. Запись данных в списки
    self.time_history.append(rel_time)

    self.gt_x_history.append(gt_x)
    self.gt_y_history.append(gt_y)

    self.enc_x_history.append(enc_x)
    self.enc_y_history.append(enc_y)

    self.cmd_x_history.append(self.cmd_x)
    self.cmd_y_history.append(self.cmd_y)

    self.pos_error_enc_history.append(err_pos_enc)
    self.pos_error_cmd_history.append(err_pos_cmd)

    self.yaw_error_enc_history.append(err_yaw_enc)
    self.yaw_error_cmd_history.append(err_yaw_cmd)

  def save_plots(self):
    os.makedirs('results', exist_ok=True)

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))

    # --- График 1: Траектории XY ---
    ax1.plot(self.gt_x_history, self.gt_y_history, 'g-', label='Ground Truth')
    ax1.plot(self.enc_x_history, self.enc_y_history, 'b--', label='Энкодеры')
    ax1.plot(self.cmd_x_history, self.cmd_y_history, 'r-.', label='Команды')
    ax1.set_title('Траектории на плоскости XY')
    ax1.set_xlabel('X, [м]')
    ax1.set_ylabel('Y, [м]')
    ax1.axis('equal')
    ax1.grid(True)
    ax1.legend()

    # --- График 2: Ошибка положения от времени ---
    ax2.plot(
        self.time_history, self.pos_error_enc_history, 'b-', label='Энкодеры')

    ax2.plot(
        self.time_history, self.pos_error_cmd_history, 'r--', label='Команды')

    ax2.set_title('Ошибка положения от времени')
    ax2.set_xlabel('Время, [с]')
    ax2.set_ylabel('Ошибка расстояния, [м]')
    ax2.grid(True)
    ax2.legend()

    # --- График 3: Ошибка угла от времени ---
    ax3.plot(
        self.time_history, self.yaw_error_enc_history, 'b-', label='Энкодеры'
    )
    ax3.plot(
        self.time_history, self.yaw_error_cmd_history, 'r--', label='Команды'
    )
    ax3.set_title('Ошибка угла (yaw) от времени')
    ax3.set_xlabel('Время, [с]')
    ax3.set_ylabel('Ошибка угла, [рад]')
    ax3.grid(True)
    ax3.legend()

    plt.tight_layout()
    output_dir = '/home/anvar/practices_ws/src/practice-03/results'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'noise.png')
    plt.savefig(output_file, dpi=300)
    # plt.savefig('results/noise_0.png', dpi=300)
    plt.close()
    self.get_logger().info(f'График сохранён в {output_file}!')

  def cmd_timer_callback(self, msg):
    self.v = msg.twist.linear.x
    self.w = msg.twist.angular.z

  def clock_timer_callback(self, msg):
    self.sim_time = msg.clock.sec + msg.clock.nanosec * 1e-9


def main(args=None):
  rclpy.init(args=args)
  node = OdometryNode()
  rclpy.spin(node)
  node.destroy_node()
  rclpy.shutdown()


if __name__ == '__main__':
  main()