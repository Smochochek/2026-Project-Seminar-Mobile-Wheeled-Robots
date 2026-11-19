import math
import os
import matplotlib
from rclpy.node import Node
import rclpy
from rosgraph_msgs.msg import Clock
import tf2_ros

matplotlib.use('Agg')
import matplotlib.pyplot as plt


def normalize_angle(angle):
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class OdometryNode(Node):

    def __init__(self):
        super().__init__('odometry_analysis')

        self.declare_parameter('duration', 60.0)
        self.declare_parameter('output_path', 'practices/practice-04/results/plot.png')
        self.declare_parameter('pos_threshold', 0.15)
        self.declare_parameter('yaw_threshold', 0.20)
        self.declare_parameter('confirm_duration', 5.0)

        self.target_duration = self.get_parameter('duration').get_parameter_value().double_value
        self.output_path = self.get_parameter('output_path').get_parameter_value().string_value
        self.pos_threshold = self.get_parameter('pos_threshold').get_parameter_value().double_value
        self.yaw_threshold = self.get_parameter('yaw_threshold').get_parameter_value().double_value
        self.confirm_duration = self.get_parameter('confirm_duration').get_parameter_value().double_value

        self.last_time = 0
        self.sim_time = 0.0

        self.not_initialized = 1
        self.start_time = 0

        self.converged = False
        self.convergence_time = None
        self.current_interval_start = None
        self.hold_time = 0.0

        self.gt_x_history = []
        self.gt_y_history = []
        self.amcl_x_history = []
        self.amcl_y_history = []

        self.pos_error_history = []
        self.yaw_error_history = []
        self.time_history = []

        self.clock_sub = self.create_subscription(
            Clock, '/clock', self.clock_timer_callback, 10
        )

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # 20 гц
        self.timer = self.create_timer(0.05, self.timer_callback)

    def quaternion_to_yaw(self, x, y, z, w):
        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        return math.atan2(siny_cosp, cosy_cosp)

    def timer_callback(self):
        current_time = self.sim_time

        # чтение поз gt и amcl из tf
        try:
            # берем последнее доступное время трансформа (Time(seconds=0))
            now_tf = rclpy.time.Time(seconds=0)
            t_gt = self.tf_buffer.lookup_transform(
                'map', 'base_link_gt', now_tf
            )
            gt_x = t_gt.transform.translation.x
            gt_y = t_gt.transform.translation.y
            q_gt = t_gt.transform.rotation
            gt_yaw = self.quaternion_to_yaw(q_gt.x, q_gt.y, q_gt.z, q_gt.w)

            t_amcl = self.tf_buffer.lookup_transform(
                'map', 'base_link', now_tf
            )
            amcl_x = t_amcl.transform.translation.x
            amcl_y = t_amcl.transform.translation.y
            q_amcl = t_amcl.transform.rotation
            amcl_yaw = self.quaternion_to_yaw(q_amcl.x, q_amcl.y, q_amcl.z, q_amcl.w)

        except (
            tf2_ros.LookupException,
            tf2_ros.ConnectivityException,
            tf2_ros.ExtrapolationException,
        ):
            return

        # фиксация t0 в момент первой оценки
        if self.not_initialized:
            self.start_time = current_time
            self.last_time = current_time
            self.not_initialized = 0
            self.get_logger().info(f'старт сбора: t0 = {self.start_time:.2f} с')
            return

        dt = current_time - self.last_time
        if dt <= 0.0:
            return
        self.last_time = current_time

        rel_time = current_time - self.start_time

        # ошибки положения и угла
        err_pos = math.hypot(amcl_x - gt_x, amcl_y - gt_y)
        err_yaw = abs(normalize_angle(amcl_yaw - gt_yaw))

        # проверка окна сходимости
        if (err_pos <= self.pos_threshold) and (err_yaw <= self.yaw_threshold):
            if self.current_interval_start is None:
                self.current_interval_start = rel_time
            self.hold_time += dt
            if (self.hold_time >= self.confirm_duration) and (not self.converged):
                self.converged = True
                self.convergence_time = self.current_interval_start
                self.get_logger().info(f'сходимость: {self.convergence_time:.2f} с')
        else:
            self.hold_time = 0.0
            self.current_interval_start = None

        if rel_time >= self.target_duration:
            self.get_logger().info('время вышло, сохранение графиков')
            self.save_plots()
            self.timer.cancel()
            return

        
        self.gt_x_history.append(gt_x)
        self.gt_y_history.append(gt_y)

        self.amcl_x_history.append(amcl_x)
        self.time_history.append(rel_time)
        self.amcl_y_history.append(amcl_y)
        self.pos_error_history.append(err_pos)
        self.yaw_error_history.append(err_yaw)

    def save_plots(self):
        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))

        # xy траектории
        ax1.plot(self.gt_x_history, self.gt_y_history, 'g-', label='GT')
        ax1.plot(self.amcl_x_history, self.amcl_y_history, 'b--', label='AMCL')

        ax1.set_title('Траектории XY')
        ax1.set_xlabel('X, [м]')
        ax1.set_ylabel('Y, [м]')

        ax1.axis('equal')
        ax1.grid(True)
        ax1.legend()

        # ошибка положения
        ax2.plot(self.time_history, self.pos_error_history, 'b-', label='Ошибка')

        ax2.axhline(self.pos_threshold, color='r', linestyle='--', label=f'Порог {self.pos_threshold} м')
        if self.converged and (self.convergence_time is not None):
            ax2.axvline(self.convergence_time, color='g', linestyle=':',
                        label=f'Сходимость {self.convergence_time:.2f} с')
        ax2.set_title('Ошибка положения')
        ax2.set_xlabel('Время, [с]')
        ax2.set_ylabel('Ошибка, [м]')
        ax2.grid(True)
        ax2.legend()

        # ошибка угла
        ax3.plot(self.time_history, self.yaw_error_history, 'm-', label='Ошибка yaw')
        ax3.axhline(self.yaw_threshold, color='r', linestyle='--', label=f'Порог {self.yaw_threshold} рад')
        if self.converged and (self.convergence_time is not None):
            ax3.axvline(self.convergence_time, color='g', linestyle=':',
                        label=f'Сходимость {self.convergence_time:.2f} с')
        ax3.set_title('Ошибка угла')
        ax3.set_xlabel('Время, [с]')
        ax3.set_ylabel('Ошибка, [рад]')
        ax3.grid(True)
        ax3.legend()

        plt.tight_layout()
        plt.savefig(self.output_path, dpi=300)
        plt.close()
        self.get_logger().info(f'график сохранен: {self.output_path}')

    def clock_timer_callback(self, msg):
        self.sim_time = msg.clock.sec + msg.clock.nanosec * 1e-9


def main(args=None):
    rclpy.init(args=args)
    node = OdometryNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
