import os
import math
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    RegisterEventHandler,
    TimerAction,
)
from launch_ros.event_handlers import OnStateTransition
from launch.conditions import IfCondition
from launch_ros.parameter_descriptions import ParameterValue
from launch.substitutions.path_join_substitution import PathJoinSubstitution
from launch import LaunchDescription
from launch_ros.actions import LifecycleNode, Node
import launch
from ament_index_python.packages import get_package_share_directory
from webots_ros2_driver.webots_launcher import WebotsLauncher
from webots_ros2_driver.webots_controller import WebotsController
from webots_ros2_driver.wait_for_controller_connection import (
    WaitForControllerConnection,
)


def generate_launch_description():
    webots_turtlebot_package_dir = get_package_share_directory(
        "webots_ros2_turtlebot"
    )
    package_dir = get_package_share_directory("practice_04")

    # параметры запуска
    world = LaunchConfiguration("world")
    localization_mode = LaunchConfiguration("localization_mode")

    error_x = LaunchConfiguration("error_x")
    error_y = LaunchConfiguration("error_y")
    error_yaw = LaunchConfiguration("error_yaw")
    # начальная поза в my_world.wbt: x = 0.0, y = -1.25, yaw = 0.0
    initial_pose_x = PythonExpression(["0.0 + float(", error_x, ")"])
    initial_pose_y = PythonExpression(["-1.25 + float(", error_y, ")"])
    initial_pose_yaw = PythonExpression(["0.0 + float(", error_yaw, ")"])

    min_particles = LaunchConfiguration("min_particles")
    max_particles = LaunchConfiguration("max_particles")

    duration = LaunchConfiguration("duration")
    output_path = LaunchConfiguration("output_path")
    pos_threshold = LaunchConfiguration("pos_threshold")
    yaw_threshold = LaunchConfiguration("yaw_threshold")
    confirm_duration = LaunchConfiguration("confirm_duration")
    run_analysis = LaunchConfiguration("run_analysis")

    mode = LaunchConfiguration("mode")
    use_rviz = LaunchConfiguration("use_rviz")
    use_sim_time = LaunchConfiguration("use_sim_time", default=True)

    # запуск webots
    webots = WebotsLauncher(
        world=PathJoinSubstitution([package_dir, "worlds", world]),
        mode=mode,
        ros2_supervisor=False,
    )

    # rviz2
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", os.path.join(package_dir, "rviz", "config.rviz")],
        parameters=[{"use_sim_time": use_sim_time}],
        condition=IfCondition(use_rviz),
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[
            {"robot_description": '<robot name=""><link name=""/></robot>'}
        ],
    )

    footprint_publisher = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        output="screen",
        arguments=["0", "0", "0", "0", "0", "0", "base_link", "base_footprint"],
    )

    # публикация карты
    map_server = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        output="screen",
        parameters=[
            {
                "use_sim_time": use_sim_time,
                "yaml_filename": PathJoinSubstitution(
                    [
                        package_dir,
                        "maps",
                        "map.yaml",
                    ]
                ),
            }
        ],
    )

    # amcl локализация
    amcl = LifecycleNode(
        package="nav2_amcl",
        executable="amcl",
        name="amcl",
        namespace="",
        output="screen",
        parameters=[
            os.path.join(package_dir, "config", "amcl.yaml"),
            {
                "use_sim_time": use_sim_time,
                "min_particles": ParameterValue(min_particles, value_type=int),
                "max_particles": ParameterValue(max_particles, value_type=int),
                "set_initial_pose": ParameterValue(
                    PythonExpression(
                        ["'", localization_mode, "' == 'initial'"]
                    ),
                    value_type=bool,
                ),
                "initial_pose.x": ParameterValue(
                    initial_pose_x, value_type=float
                ),
                "initial_pose.y": ParameterValue(
                    initial_pose_y, value_type=float
                ),
                "initial_pose.yaw": ParameterValue(
                    initial_pose_yaw, value_type=float
                ),
            },
        ],
    )

    # lifecycle менеджер для map_server и amcl
    lifecycle = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_localization",
        output="screen",
        parameters=[
            {
                "use_sim_time": use_sim_time,
                "autostart": True,
                "node_names": ["map_server", "amcl"],
            }
        ],
    )

    # глобальная реинициализация частиц для режима global
    global_initializer = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=amcl,
            goal_state="active",
            entities=[
                TimerAction(
                    period=2.0,
                    actions=[
                        ExecuteProcess(
                            cmd=[
                                "ros2",
                                "service",
                                "call",
                                "/reinitialize_global_localization",
                                "std_srvs/srv/Empty",
                                "{}",
                            ],
                            output="screen",
                        )
                    ],
                )
            ],
        ),
        condition=IfCondition(
            PythonExpression(["'", localization_mode, "' == 'global'"])
        ),
    )

    # супервизор gt и clock
    supervisor_driver = WebotsController(
        robot_name="ground_truth_supervisor",
        parameters=[
            {
                "robot_description": os.path.join(
                    package_dir, "resource", "ground_truth_supervisor.urdf"
                ),
                "use_sim_time": use_sim_time,
            }
        ],
        respawn=True,
    )

    controller_manager_timeout = ["--controller-manager-timeout", "50"]

    diffdrive_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        arguments=[
            "diffdrive_controller",
            "--controller-ros-args=-p diffdrive_controller:wheel_separation_multiplier:=1.1",
        ]
        + controller_manager_timeout,
    )
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        arguments=["joint_state_broadcaster"] + controller_manager_timeout,
    )
    ros_control_spawners = [
        diffdrive_controller_spawner,
        joint_state_broadcaster_spawner,
    ]

    robot_description_path = os.path.join(
        webots_turtlebot_package_dir, "resource", "turtlebot_webots.urdf"
    )
    ros2_control_params = os.path.join(
        webots_turtlebot_package_dir, "resource", "ros2control.yml"
    )
    turtlebot_driver = WebotsController(
        robot_name="TurtleBot3Burger",
        parameters=[
            {
                "robot_description": robot_description_path,
                "use_sim_time": use_sim_time,
                "set_robot_state_publisher": True,
            },
            ros2_control_params,
        ],
        remappings=[
            ("/diffdrive_controller/cmd_vel", "/cmd_vel"),
            ("/diffdrive_controller/odom", "/odom"),
        ],
        respawn=True,
    )

    # движение по кругу (v=0.2, w=0.16)
    velocity_publisher = Node(
        package='practice_04',
        executable='circle_drive',
        name='circle_drive',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
    )

    # узел анализа сходимости и графиков
    analysis_node = Node(
        package="practice_04",
        executable="odometry_analysis",
        name="odometry_analysis",
        output="screen",
        parameters=[{
            "duration": duration,
            "output_path": output_path,
            "pos_threshold": pos_threshold,
            "yaw_threshold": yaw_threshold,
            "confirm_duration": confirm_duration,
            "use_sim_time": use_sim_time,
        }],
        condition=IfCondition(run_analysis),
    )

    waiting_nodes = WaitForControllerConnection(
        target_driver=turtlebot_driver, nodes_to_start=ros_control_spawners
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "world",
                default_value="my_world.wbt",
                description="Scene file from worlds directory",
            ),
            DeclareLaunchArgument(
                "localization_mode",
                default_value="global",
                choices=["global", "initial"],
                description="AMCL initialization mode: global or initial",
            ),
            DeclareLaunchArgument(
                "error_x",
                default_value="0.0",
                description="Initial error x (m)",
            ),
            DeclareLaunchArgument(
                "error_y",
                default_value="0.0",
                description="Initial error y (m)",
            ),
            DeclareLaunchArgument(
                "error_yaw",
                default_value="0.0",
                description="Initial error yaw (rad)",
            ),
            DeclareLaunchArgument(
                "min_particles",
                default_value="200",
                description="AMCL min particles",
            ),
            DeclareLaunchArgument(
                "max_particles",
                default_value="800",
                description="AMCL max particles",
            ),
            DeclareLaunchArgument(
                "duration",
                default_value="60.0",
                description="Experiment duration in seconds",
            ),
            DeclareLaunchArgument(
                "output_path",
                default_value="/home/anvar/mobile-robots-project-seminar/practices/practice-04/results/plot.png",
                description="Path to save result plot",
            ),
            DeclareLaunchArgument(
                "pos_threshold",
                default_value="0.15",
                description="Position convergence threshold (m)",
            ),
            DeclareLaunchArgument(
                "yaw_threshold",
                default_value="0.20",
                description="Yaw convergence threshold (rad)",
            ),
            DeclareLaunchArgument(
                "confirm_duration",
                default_value="5.0",
                description="Continuous confirmation window (s)",
            ),
            DeclareLaunchArgument(
                "run_analysis",
                default_value="true",
                description="Whether to run convergence analysis node",
            ),
            DeclareLaunchArgument(
                "mode",
                default_value="realtime",
                description="Webots startup mode",
            ),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="true",
                description="Start RViz2",
            ),

            webots,
            rviz,
            robot_state_publisher,
            footprint_publisher,
            map_server,
            global_initializer,
            amcl,
            lifecycle,
            supervisor_driver,
            turtlebot_driver,
            velocity_publisher,
            waiting_nodes,
            analysis_node,

            launch.actions.RegisterEventHandler(
                event_handler=launch.event_handlers.OnProcessExit(
                    target_action=webots,
                    on_exit=[
                        launch.actions.EmitEvent(event=launch.events.Shutdown())
                    ],
                )
            ),
        ]
    )
