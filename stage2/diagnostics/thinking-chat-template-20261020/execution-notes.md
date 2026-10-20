# 执行说明

首次运行在生成前的输入核验处停止：Transformers 5.14.1 的 apply_chat_template 返回 BatchEncoding，检查脚本将其误与 token 列表比较。实际 token 完全一致。已改为读取 input_ids 后继续；未产生失败模型回答，模板与推理参数未改动。
