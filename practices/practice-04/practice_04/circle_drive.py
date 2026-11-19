#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped


class CircleDrive(Node):
    def __init__(self):
        super().__init__('circle_drive')

        self.linear_speed = 0.2
        self.angular_speed = 0.16

        self.publisher_ = self.create_publisher(TwistStamped, '/cmd_vel', 10)
        self.timer = self.create_timer(0.1, self.timer_callback)

    def timer_callback(self):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.twist.linear.x = self.linear_speed
        msg.twist.angular.z = self.angular_speed
        self.publisher_.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = CircleDrive()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
