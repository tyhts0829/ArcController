IPC 戦略の提案（改善版）

現在の実装を分析した結果、以下の戦略を提案します：

1. 責任の分離

現状の送信方式：

- MidiSender: 音楽機器向け（DAW、シンセサイザー）
- AioOscSender: ビジュアルソフトウェア向け（TouchDesigner、Max/MSP）
- IPC（新規）: Python クリエイティブコーディング向け（Processing.py、独自スクリプト）

2. IPC 実装案（改善版）

方式: 名前付き共有メモリ + Lock

```python
# arc/__init__.py に追加
from multiprocessing import shared_memory, Lock
import numpy as np

class ArcValues:
    def __init__(self):
        try:
            self._shm = shared_memory.SharedMemory(name="arc_controller")
        except FileNotFoundError:
            raise ConnectionError("ArcController not running")

        self._lock = Lock()
        self._values = np.ndarray((4, 4), dtype=np.float32, buffer=self._shm.buf)

    @property
    def layer(self):
        """現在のアクティブレイヤー"""
        return LayerProxy(self._values[self._active_layer_index])

    @property
    def ring(self):
        """アクティブレイヤーのrings"""
        return self.layer.rings

    @property
    def layers(self):
        """全レイヤーへのアクセス"""
        return [LayerProxy(self._values[i]) for i in range(4)]

# 使用例
import arc
values = arc.ipc()  # ConnectionError if not running
print(values.ring[0])  # アクティブレイヤーのring 0
print(values.layers[2].rings[1])  # レイヤー2のring 1
```

3. 主要な改善点

- **ライフサイクル管理**: 名前付き共有メモリで既存プロセス検出
- **エラーハンドリング**: ArcController 未起動時の ConnectionError
- **同期メカニズム**: multiprocessing.Lock でデータ整合性保証
- **API 一貫性**: arc.layer/arc.ring/arc.layers の直感的な階層

4. 実装の段階的アプローチ（修正版）

Phase 1: 読み取り専用 API + エラーハンドリング

- arc.ring[n] で現在値を取得
- arc.layers[n].rings[m] でレイヤー指定アクセス
- 共有メモリで低レイテンシ実現
- 適切なエラーハンドリング

Phase 2: イベント通知システム

```python
@arc.on_ring_change(0)
def handle_ring(value):
    print(f"Ring 0: {value}")
```

Phase 3: 双方向通信

- arc.ring[0] = 0.5 で値を設定可能に
- LFO の外部制御
- プリセット切替 API

5. 技術的課題と対策

- **プロトタイプ検証**: 実装前に共有メモリアプローチの動作確認
- **リソース競合**: 複数クライアントでの同時アクセス制御

6. 利点

- 低レイテンシ: 共有メモリで直接アクセス
- 堅牢性: エラーハンドリングとライフサイクル管理
- 既存システムとの共存: MIDI/OSC と独立して動作
- Python ネイティブ: numpy 配列で効率的なデータ処理

この改善された戦略により、creative coding 環境での使いやすさと、既存の音楽/ビジュアル機器との互換性、そして堅牢性を両立できます。
