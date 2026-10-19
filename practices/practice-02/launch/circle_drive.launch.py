import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    pkg_dir = get_package_share_directory('practice_02')

    main_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_dir, 'launch', 'spawn_robot.launch.py')
        )
    )

    drive_process = ExecuteProcess(
        cmd=[
            'ros2', 'topic', 'pub', '-r', '10', '/cmd_vel', 'geometry_msgs/msg/TwistStamped',
            '{header: {stamp: {sec: 0, nanosec: 0}, frame_id: "base_link"}, twist: {linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.16}}}'
        ],
        output='screen'
    )

    return LaunchDescription([
        main_launch,
        drive_process,
    ])
