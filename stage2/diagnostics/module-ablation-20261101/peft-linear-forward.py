    def forward(self, x: torch.Tensor, *args: Any, **kwargs: Any) -> torch.Tensor:
        self._check_forward_args(x, *args, **kwargs)
        adapter_names = kwargs.pop("adapter_names", None)
        variant_kwargs = {k: kwargs.pop(k, None) for k in VARIANT_KWARG_KEYS}  # don't pass these to base_layer

        if self.disable_adapters:
            if self.merged:
                self.unmerge()
            result = self.base_layer(x, *args, **kwargs)
        elif adapter_names is not None:
            result = self._mixed_batch_forward(x, *args, adapter_names=adapter_names, **variant_kwargs, **kwargs)
        elif self.merged:
            result = self.base_layer(x, *args, **kwargs)
        else:
            result = self.base_layer(x, *args, **kwargs)
            torch_result_dtype = result.dtype

            lora_A_keys = self.lora_A.keys()
            for active_adapter in self.active_adapters:
                if active_adapter not in lora_A_keys:
                    continue

                lora_A = self.lora_A[active_adapter]
                lora_B = self.lora_B[active_adapter]
                dropout = self.lora_dropout[active_adapter]
                scaling = self.scaling[active_adapter]
                x = self._cast_input_dtype(x, lora_A.weight.dtype)
                if active_adapter not in self.lora_variant:  # vanilla LoRA
                    result = result + lora_B(lora_A(dropout(x))) * scaling
                else:
                    result = self.lora_variant[active_adapter].forward(
                        self,
                        active_adapter=active_adapter,
                        x=x,
                        result=result,
                        **variant_kwargs,
                        **kwargs,
                    )

            result = result.to(torch_result_dtype)

        return result
