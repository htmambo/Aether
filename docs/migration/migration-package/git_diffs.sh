#!/bin/bash
# 提取修改文件的 diff 用于参考

echo "提取 git diff..."

# 后端修改��件
echo "=== src/models/endpoint_models.py ===" > diffs.txt
git show edb3710 -- src/models/endpoint_models.py >> diffs.txt
echo -e "\n\n" >> diffs.txt

echo "=== src/api/handlers/base/request_builder.py ===" >> diffs.txt
git show edb3710 -- src/api/handlers/base/request_builder.py >> diffs.txt
echo -e "\n\n" >> diffs.txt

echo "=== src/services/provider/transport.py ===" >> diffs.txt
git show edb3710 -- src/services/provider/transport.py >> diffs.txt
echo -e "\n\n" >> diffs.txt

echo "=== src/api/handlers/base/endpoint_checker.py ===" >> diffs.txt
git show edb3710 -- src/api/handlers/base/endpoint_checker.py >> diffs.txt
echo -e "\n\n" >> diffs.txt

# 前端修改文件
echo "=== frontend/src/features/providers/components/EndpointFormDialog.vue ===" >> diffs.txt
git show edb3710 -- frontend/src/features/providers/components/EndpointFormDialog.vue >> diffs.txt
echo -e "\n\n" >> diffs.txt

echo "=== frontend/src/api/endpoints/types.ts ===" >> diffs.txt
git show edb3710 -- frontend/src/api/endpoints/types.ts >> diffs.txt 2>/dev/null || echo "文件未修改或不存在"

echo "diffs.txt 已生成"
