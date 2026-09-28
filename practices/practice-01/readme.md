
1) запустить контейнер: HOST_XAUTHORITY="$XAUTHORITY" docker compose --env-file .env --env-file .env.local -f docker-compose.yaml up -d
2) перейти в папку с проектом: cd practices_ws
3) собрать рос2 пакет: colcon build --symlink-install --packages-select digit_drawer
4) обновить путь(вроде): source install/setup.zsh
5) запустить лаун-файл: ros2 launch digit_drawer drawer.launch.py
