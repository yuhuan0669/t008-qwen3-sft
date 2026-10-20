# T-008 GPU SFT最终门禁

本次一轮SFT候选完成，训练后已恢复原服务；随后按新指示加载独立LoRA测试入口。当前base+test双入口，训练窗口结束，未作正式生产发布。

| 条件 | 状态 |
|---|---|
| native_recipe_and_CPU | PASS |
| actual_job_PVC_and_runtime | PASS |
| GPU_window_authorization | EXPLICIT_USER_AUTHORIZATION_CONSUMED |
| Smoke_3_steps | PASS |
| Full_1epoch_final_checkpoint | PASS |
| ClearML_model_upload_and_hash_readback | PASS |
| original_vllm_restore | PASS |
| independent_ABCD_evaluation | NOT_EXECUTED |
| model_quality_acceptance | NOT_GRANTED |
| deployment_publication | NO_FORMAL_RELEASE_OR_QUALITY_ACCEPTANCE |
| user_authorized_test_LoRA_serving | PASS_TEST_ONLY |
| OpenWebUI_tool_choice_auto_compatibility | PASS_HTTP200_SINGLE_REQUEST |

训练完成不代表模型验收通过。后续独立评测/优化/上线未执行，不沿用本次窗口自动启动。
