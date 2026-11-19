import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'practice_04'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
        (os.path.join('share', package_name, 'worlds'), glob(os.path.join('worlds', '*.wbt'))),
        (os.path.join('share', package_name, 'protos'), glob(os.path.join('protos', '*.proto'))),
        (os.path.join('share', package_name, 'resource'), glob(os.path.join('resource', '*.*'))),
        (os.path.join('share', package_name, 'maps'), glob(os.path.join('maps', '*.*'))),
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.*'))),
        (os.path.join('share', package_name, 'rviz'), glob(os.path.join('rviz', '*.*'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Anvar Uziaev',
    maintainer_email='aaouzyaev@edu.hse.ru',
    description='Practice 04: Localization in Webots with AMCL',
    license='Apache-2.0',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'circle_drive = practice_04.circle_drive:main',
            'odometry_analysis = practice_04.odometry_analysis:main',
        ],
    },
)
