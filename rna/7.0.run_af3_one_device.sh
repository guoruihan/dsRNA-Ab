#!/usr/bin/env bash

# Usage:
#   ./run_af3_on_device.sh <device> <input_dir> <output_dir>
#
# Example:
#   ./run_af3_on_device.sh 3 /path/to/input /path/to/output

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <device> <input_dir> <output_dir>"
  exit 1
fi

DEVICE="$1"
INPUT_DIR="$2"
OUTPUT_DIR="$3"

# Python 可执行环境
PYTHON_BIN="/datapool/data2/home/pengxingang/anaconda3/envs/af3/bin/python"

# AF3 脚本位置
RUN_SCRIPT="/datapool/data2/home/pengxingang/data3/pengxingang/af3/alphafold3/run_alphafold.py"

# 模型目录与数据库目录（如果你希望也能参数化，可以把它们也做成参数）
MODEL_DIR="/datapool/data2/home/pengxingang/data3/pengxingang/af3/alphafold3/models/"
DB_DIR="/datapool/data2/home/pengxingang/data3/pengxingang/af3/alphafold3/database/"

# 设定可见 GPU 设备
export CUDA_VISIBLE_DEVICES="${DEVICE}"

# 执行 AF3 脚本
"${PYTHON_BIN}" "${RUN_SCRIPT}" \
    --model_dir="${MODEL_DIR}" \
    --db_dir="${DB_DIR}" \
    --input_dir="${INPUT_DIR}" \
    --output_dir="${OUTPUT_DIR}" \
    --max_template_date=2022-01-01

