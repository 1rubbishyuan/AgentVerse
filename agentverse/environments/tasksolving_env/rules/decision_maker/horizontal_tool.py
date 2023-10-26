from __future__ import annotations
import json
import asyncio
from copy import deepcopy
from colorama import Fore
from itertools import cycle

from typing import TYPE_CHECKING, List

from . import decision_maker_registry
from .base import BaseDecisionMaker
from agentverse.logging import logger
from agentverse.message import SolverMessage, Message

if TYPE_CHECKING:
    from agentverse.agents.base import BaseAgent
    from agentverse.message import CriticMessage


@decision_maker_registry.register("horizontal-tool")
class HorizontalToolDecisionMaker(BaseDecisionMaker):
    """
    Discuss in a horizontal manner.
    """

    name: str = "horizontal_tool"
    tools: List[dict] = []
    tool_names: List[str] = []
    tool_config: str = None

    def __init__(self, *args, **kwargs):
        assert kwargs.get("tool_config", None) is not None
        with open(kwargs.get("tool_config"), "r") as f:
            tools_dict = json.load(f)
        tools = tools_dict["tools_json"]
        tool_names = [t["name"] for t in tools]
        super().__init__(tools=tools, tool_names=tool_names, *args, **kwargs)

    # def step(
    async def astep(
        self,
        agents: List[BaseAgent],
        task_description: str,
        previous_plan: str = "No solution yet.",
        advice: str = "No advice yet.",
        **kwargs,
    ) -> List[str]:
        agents[0].memory.reset()
        if advice != "No advice yet.":
            self.broadcast_messages(
                agents[1:], [Message(content=advice, sender="Evaluator")]
            )
        all_roles = "\n".join(
            [f"{agent.name}: {agent.role_description}" for agent in agents[1:]]
        )  # 应该就是要改这里了，把这里改为建立DAG来让计划更加地明确和可见
        # 大致的思路为：首先把openai的输出按照一定的格式化，然后读取这样的格式化后去根据格式化的输出来提取信息并使用第三方的库来进行DAG的生成
        end_flag = False
        discussion_cnt = 0
        for agent in cycle(agents[1:]):
            discussion_cnt += 1
            review: CriticMessage = await agent.astep(
                previous_plan, advice, task_description, all_roles
            )
            if review.content.strip().endswith("[END]"):
                review.content = review.content.strip().replace("[END]", "")
                if discussion_cnt >= len(agents) - 1:
                    # Force all the agents to speak at least once.
                    end_flag = True
            if review.content != "":
                self.broadcast_messages(
                    agents, [review]
                )  # because of this , criticagents can communacate with each other (utilize memory mechnism)

            logger.info("", "Reviews:", Fore.YELLOW)
            logger.info(
                "",
                f"[{review.sender}]: {review.content}",
                Fore.YELLOW,
            )
            if end_flag:
                break

        result: SolverMessage = agents[0].step(
            previous_plan, advice, task_description
        )  # What I need to do is normalizing the SolverMessage into DAG
        result_list = []
        for res in result.content:
            res_tmp = deepcopy(result)
            res_tmp.content = " - ".join(res)
            result_list.append(res_tmp)  # 大致就是要修改这里，我想要出了输出name和plan外还输出一个可以拓扑排序的信息
        return result_list  # 目前的agents在做ReAct的过程中之间是没有交流的

    def reset(self):
        pass
