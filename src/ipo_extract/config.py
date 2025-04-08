from dotenv import load_dotenv
import os


def load_config():
    # 1. 读取当前环境（默认 dev）
    current_env = os.getenv("APP_ENV", "dev")

    # 2. 加载对应的 .env 文件
    env_file = f".env.{current_env}"
    if os.path.exists(env_file):
        load_dotenv(env_file)
    else:
        load_dotenv()  # 回退到默认 .env

    # 3. 返回配置字典
    return {
        "env": current_env,
        "api_key": os.getenv("BAILIAN_API_KEY")
    }

# 初始化配置
config = load_config()