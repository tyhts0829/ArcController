import time

import arc

if __name__ == "__main__":
    # 手動でのスタート/ストップ制御
    print("Manual control example...")

    # 開始
    if arc.start():
        print("ArcController started successfully.")
    else:
        print("Failed to start or already running.")
        exit(1)

    # 状態確認
    print(f"Running status: {arc.is_running()}")

    # 何かの処理をシミュレート
    print("Doing work for 3 seconds...")
    time.sleep(3)

    # 停止
    if arc.stop():
        print("ArcController stopped successfully.")
    else:
        print("Failed to stop or not running.")

    print(f"Final status: {arc.is_running()}")
