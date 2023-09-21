# Copyright 2022 MosaicML LLM Foundry authors
# SPDX-License-Identifier: Apache-2.0


FROM mosaicml/llm-foundry:2.0.1_cu118-latest


# Install and uninstall foundry to cache foundry requirements
RUN git clone -b main https://github.com/mosaicml/llm-foundry.git && \
    cd llm-foundry && \
    pip install -e ".[gpu]" 

WORKDIR /llm-foundry

ENTRYPOINT ["ls", "-la"]