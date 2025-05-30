import arc

if __name__ == "__main__":
    # ArcControllerをバックグラウンドで開始
    if arc.start():
        print("ArcController started successfully in background.")

        # 状態確認
        print(f"Is running: {arc.is_running()}")

        # 必要に応じて停止
        # arc.stop()
    else:
        print("Failed to start ArcController or already running.")
