# Reflection

**What are the limitations or biases in your system?**

The agent only moves tasks to nearby hours with no awareness of real-world constraints, like walks belong in the morning. It also assumes task descriptions are unique per pet, and the free-tier API quota runs out quickly under active use.

**Could your AI be misused, and how would you prevent that?**

The agent could propose technically valid but impractical changes (e.g., a walk at 2 AM). The human review step prevents any change from being applied without user approval, and all tool inputs are validated.

**What surprised you while testing your AI's reliability?**

The mocked tests passed easily, but the first live run immediately hit a 429 quota error. That gap between "tests pass" and "it actually works" was a good reminder that mocks prove logic, not infrastructure.

**Describe your collaboration with AI during this project. Identify one instance when the AI gave a helpful suggestion and one instance where its suggestion was flawed or incorrect.**

Helpful: pre-loading the current tasks and conflicts into the agent's first message rather than having it call get_tasks and get_conflicts as separate tool calls, cutting API usage.

Flawed: it initially suggested using the `google-generativeai` package, which turned out to be deprecated
