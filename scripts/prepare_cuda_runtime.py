"""Install the separately pinned official Ubuntu CUDA runtime in the workspace."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.generation.cuda_runtime import prepare_cuda_runtime  # noqa: E402

if __name__ == "__main__":
    print(prepare_cuda_runtime()[0])
