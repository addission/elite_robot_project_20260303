# 文件路径: /home/yff/elite_ros_ws/src/tcp_bridge/launch/cs625_launcher.py
# (已为您修正为与我们当前代码匹配的正确版本)

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    # 获取RViz配置文件的完整路径
    rviz_config_file = os.path.join(
        get_package_share_directory('tcp_bridge'),
        'rviz',
        'default.rviz' # 确保你的RViz配置文件叫这个名字
    )

    return LaunchDescription([
        # 启动 RViz
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config_file],
            output='screen'
        ),
        
        # === 启动我们项目中实际使用的3个节点 ===

        # 1. 启动 tcp_server 节点 (接收 "S1,..." 数据)
        Node(
            package='tcp_bridge',
            executable='tcp_server',
            name='tcp_server',
            output='screen',
            prefix='xterm -e' # 在新终端中运行，方便观察和调试
        ),
        
        # 2. 启动 pose_displayer 节点 (在RViz中显示TF)
        Node(
            package='tcp_bridge',
            executable='pose_to_tf_broadcaster',
            name='pose_to_tf_broadcaster',
            output='screen' # 这个节点日志不多，可以在主窗口输出
        ),
        
        # 3. 启动 robot_commander 节点 (发送指令给真实机器人)
        Node(
            package='tcp_bridge',
            executable='robot_commander',
            name='robot_commander',
            output='screen',
            prefix='xterm -e' # 在新终端中运行，方便观察与机器人的通信
        ),
    ])


