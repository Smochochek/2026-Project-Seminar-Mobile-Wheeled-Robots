# Практическая работа 2 (Вариант 16)

**Выполнил:** Узяев Анвар  
**Вариант:** 16 (цифры «1» и «6»)

## 1. Подготовка на хосте macOS
В терминале Mac запустить сервер Webots:
```bash
export WEBOTS_HOME=/Applications/Webots.app
python3 Downloads/local_simulation_server.py
python3 Downloads/Patch_webots_macos26.py
```

## 2. Подготовка в виртуальной машине (UTM / Linux)
Запуск и сброс кэша контейнера:
```bash
cd ~/mobile-robots-project-seminar
HOST_XAUTHORITY="$XAUTHORITY" docker compose --env-file .env --env-file .env.local -f docker-compose.yaml -f docker-compose.gpu.yaml -f docker-compose.webots-mac.yaml up -d
docker restart $(docker ps -q -f name=ros2)
```

Вход в контейнер:
```bash
HOST_XAUTHORITY="$XAUTHORITY" docker compose --env-file .env --env-file .env.local -f docker-compose.yaml -f docker-compose.gpu.yaml -f docker-compose.webots-mac.yaml exec -it ros2-base zsh
```

## 3. Сборка пакета (внутри контейнера)
```bash
cd ~/practices_ws
colcon build --packages-select practice_02 --symlink-install
source install/setup.zsh
```

## 4. Запуск симуляции и движения робота (строго по ТЗ)

### Способ 1 (публикация команды из терминала с помощью ros2 topic pub):
1. В первом терминале запустить симуляцию:
```bash
ros2 launch practice_02 spawn_robot.launch.py
```
2. Во втором терминале запустить движение по кругу:
```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/TwistStamped "{header: {stamp: {sec: 0, nanosec: 0}, frame_id: 'base_link'}, twist: {linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.16}}}"
```

### Способ 2 (запуск через второй launch-файл):
Запуск одной командой симуляции и публикации скорости:
```bash
ros2 launch practice_02 circle_drive.launch.py
```
