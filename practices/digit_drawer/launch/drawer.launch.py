from launch import LaunchDescription
from launch.actions import (
    ExecuteProcess,
    LogInfo,
    RegisterEventHandler,
    TimerAction,
)
from launch.event_handlers import OnProcessStart
from launch_ros.actions import Node


def generate_launch_description():

    # 1. Запуск окна симулятора
    turtlesim = Node(
        package="turtlesim",
        executable="turtlesim_node",
        name="turtlesim",
        output="screen",
    )
    kill_turtle = ExecuteProcess(
    cmd=[
        "ros2",
        "service",
        "call",
        "/kill",
        "turtlesim/srv/Kill",
        "{name: turtle1}",
    ],
    output="screen",
    )

    spawn_turtle = ExecuteProcess(
        cmd=[
            "ros2",
            "service",
            "call",
            "/spawn",
            "turtlesim/srv/Spawn",
            "{x: 2.0, y: 3.0, theta: 0.0, name: 'turtle3'}",
        ],
        output="screen",
    )

    # 2. Спавн второй черепахи turtle2 со смещением вправо
    spawn_turtle2 = ExecuteProcess(
        cmd=[
            "ros2",
            "service",
            "call",
            "/spawn",
            "turtlesim/srv/Spawn",
            "{x: 6.5, y: 3.0, theta: 0.0, name: 'turtle2'}",
        ],
        output="screen",
    )

    # 3. Первая черепаха (turtle1) рисует десятки
    drawer_tens = Node(
        package="digit_drawer",
        executable="drawer",
        name="drawer_tens",
        output="screen",
        parameters=[
            {
                "turtle": "turtle3",
                "digit": 2,
                "offset_x": 2.0,
                "offset_y": 3.0,
                "scale": 1.6,
            }
        ],
    )

    # 4. Вторая черепаха (turtle2) рисует единицы 
    drawer_units = Node(
        package="digit_drawer",
        executable="drawer",
        name="drawer_units",
        output="screen",
        parameters=[
            {
                "turtle": "turtle2",
                "digit": 1,          
                "offset_x": 6.0,
                "offset_y": 3.0,
                "scale": 1.6,
            }
        ],
    )

    return LaunchDescription(
        [
            turtlesim,
            # После старта симулятора сразу спавним вторую черепаху
            RegisterEventHandler(
                OnProcessStart(
                    target_action=turtlesim,
                    on_start=[
                        LogInfo(msg="спавн turtle2..."),
                        kill_turtle,
                        spawn_turtle,
                        spawn_turtle2,
                    ],
                )
            ),

            TimerAction(
                period=1.0,
                actions=[
                    LogInfo(msg="запуск рисования цифр..."),
                    drawer_tens,
                    drawer_units,
                ],
            ),
        ]
    )