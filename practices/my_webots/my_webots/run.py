#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
import math

class SafeEightDriver(Node):
    def __init__(self):
        super().__init__('figure_eight_driver')
        self.pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)


        self.v = 0.16                                       
        self.radius = 0.45                                  
        self.w_curve = self.v / self.radius                 

        # 2. Тайминги участков
        self.t_turn180 = math.pi / self.w_curve
        self.t_straight_full = 1.1 / self.v
        self.t_straight_start = self.t_straight_full / 2.0

        self.w_turn_inplace = -0.40
        self.t_turn_inplace = (math.pi / 2.0) / abs(self.w_turn_inplace)
        self.t_init = self.t_turn_inplace + self.t_straight_start


        self.cycle_duration = 4.0 * self.t_turn180 + 4.0 * self.t_straight_full

        self.timer_period = 0.05
        self.timer = self.create_timer(self.timer_period, self.timer_callback)
        self.elapsed = 0.0
        self.get_logger().info('Safe Eight Driver запущен!')

    def timer_callback(self):
        msg = TwistStamped()

        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'

        if self.elapsed < self.t_turn_inplace:
            v_cmd = 0.0
            w_cmd = self.w_turn_inplace

        elif self.elapsed < self.t_init:
            v_cmd = self.v
            w_cmd = 0.0

        else:
            t = (self.elapsed - self.t_init) % self.cycle_duration

            t1 = self.t_turn180
            t2 = t1 + self.t_straight_full
            t3 = t2 + self.t_turn180
            t4 = t3 + self.t_straight_full
            t5 = t4 + self.t_turn180
            t6 = t5 + self.t_straight_full
            t7 = t6 + self.t_turn180

            if t < t1:
                # 1 направо
                v_cmd, w_cmd = self.v, -self.w_curve
            elif t < t2:
                # 2. Прямо
                v_cmd, w_cmd = self.v, 0.0
            elif t < t3:
                # 3. направо
                v_cmd, w_cmd = self.v, -self.w_curve
            elif t < t4:
                # 4. Прямо
                v_cmd, w_cmd = self.v, 0.0
            elif t < t5:
                # 5. налево
                v_cmd, w_cmd = self.v, self.w_curve
            elif t < t6:
                # 6. Прямо
                v_cmd, w_cmd = self.v, 0.0
            elif t < t7:
                # 7. налево
                v_cmd, w_cmd = self.v, self.w_curve
            else:
                # 8. Прямо
                v_cmd, w_cmd = self.v, 0.0

        msg.twist.linear.x = float(v_cmd)
        msg.twist.linear.y = 0.0
        msg.twist.linear.z = 0.0
        msg.twist.angular.x = 0.0
        msg.twist.angular.y = 0.0
        msg.twist.angular.z = float(w_cmd)

        self.pub.publish(msg)
        self.elapsed += self.timer_period

def main(args=None):
    rclpy.init(args=args)
    node = SafeEightDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        stop = TwistStamped()
        stop.header.stamp = node.get_clock().now().to_msg()
        stop.header.frame_id = 'base_link'
        node.pub.publish(stop)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()