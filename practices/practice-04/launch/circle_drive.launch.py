import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='practice_04',
            executable='circle_drive',
            name='circle_drive',
            output='screen',
            parameters=[{
                'linear_speed': 0.2,
                'angular_speed': 0.16,
                'use_sim_time': True,
            }]
        )
    ])
