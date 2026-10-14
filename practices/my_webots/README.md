0) cd mobile-robots-project-seminar/
1)запуск контейнера
HOST_XAUTHORITY="$XAUTHORITY" docker compose --env-file .env --env-file .env.local -f docker-compose.yaml -f docker-compose.gpu.yaml -f docker-compose.webots-mac.yaml up -d
2) вход в него в двух терминалах
HOST_XAUTHORITY="$XAUTHORITY" docker compose --env-file .env --env-file .env.local -f docker-compose.yaml -f docker-compose.gpu.yaml -f docker-compose.webots-mac.yaml exec -it ros2-base zsh
3) билд проекта, обновление путей 
colcon build --packages-select my_webots --symlink-install
source install/setup.zsh
5) запуск протокола питон с портом 2000, запуск патча из-за бага в терминалах мака
export WEBOTS_HOME=/Applications/Webots.app
python3 Downloads/local_simulation_server.py
python3 Downloads/Patch_webots_macos26.py

7) перезапуск контейнера (без него у меня робот не едет) в терминале линукса
docker restart $(docker ps -q -f name=ros2)

6)запуск робота
ros2 launch my_webots spawn_robot.launch.py

7) запуск протокола поездки робота

python3 ws_practices/src/my_webots/my_webots/run.py
