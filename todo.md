- 長押しで設定モード。そこで preset をサイクルさせる。短押しはレイヤーサイクルはそのままで。
- midi cc 変更機能
- 慣性機能 static な値移動に慣性、あるいは摩擦を考慮した挙動

IPC 戦略の提案

現在の実装を分析した結果、以下の戦略を提案します：

1. 責任の分離

現状の送信方式：

- MidiSender: 音楽機器向け（DAW、シンセサイザー）
- AioOscSender: ビジュアルソフトウェア向け（TouchDesigner、Max/MSP）
- IPC（新規）: Python クリエイティブコーディング向け（Processing.py、独自スクリプト）

2. IPC 実装案

方式 1: 共有メモリベース（推奨）

# arc/**init**.py に追加

from multiprocessing import shared_memory
import numpy as np

class ArcValues:
def **init**(self):
self.\_shm = shared_memory.SharedMemory(create=True, size=64)
self.\_values = np.ndarray((4, 4), dtype=np.float32, buffer=self.\_shm.buf)

      def __getitem__(self, idx):
          return RingProxy(self._values[0, idx])  # active layer

# 使用例

import arc
values = arc.ipc() # 後続の処理をブロッキングしない
print(values.ring[0]) # ring0 の value を取得

3. アーキテクチャ統合案

4. 実装の段階的アプローチ

Phase 1: 読み取り専用 API

- arc.ring[n] で現在値を取得
- arc.layer[n].ring[m] でレイヤー指定アクセス
- 共有メモリで低レイテンシ実現

Phase 2: 双方向通信

- arc.ring[0] = 0.5 で値を設定可能に
- LFO の外部制御
- プリセット切替 API

Phase 3: イベントベース API

# コールバック登録

@arc.on_ring_change(0)
def handle_ring(value):
print(f"Ring 0: {value}")

5. 利点

- 低レイテンシ: 共有メモリで直接アクセス
- シンプルな API: arc.ring[n]の直感的な記法
- 既存システムとの共存: MIDI/OSC と独立して動作
- Python ネイティブ: numpy 配列で効率的なデータ処理

この戦略により、creative coding 環境での使いやすさと、既存の音楽/ビジュアル機器との互換性を両立できます。
