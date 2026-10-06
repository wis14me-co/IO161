# overall layout
  The factory uses 4 agents with 1 for planning and 3 for implemetetion. Also, the agent responsible for planning is also responsible for reviewing at stage end

# Factory predictability

  The factory uses strict mandates with clear rules, so that the output can stay relatively predictable and easier to manage.
  The mandates mention that to focus on convenience and simplicity. So, the agents after writting each files of code, tested each ones written code. Which was not included in mandate but counted as a test which complies with the rules written in mandate disallowing self review as this test was not accounted for total error check, rather part of writting the code.

# encountered problems

  It took 18 - 25 differant sesions and over 50+ hours of nonstop monitoring and fixing. First problem was integration of API's, which I wrote custom scripts to implement, but after considering my options I integrated codex cli instead. It resulted in incomplete stage files. The abandoned script implentation resulted in waste of time and therefore became problem.
  Although codex was a solid choice, it limitation was its limit. During testing it showed great compatibilty, but since I was using free tier and due to some connection errors that were un-noticed, all of my credits ran out. 
  In 1st october, I got opencode integrated. After testing and integrating differant API's, many were shown incompatible. So, after careful consideration I choose nemotron 3 ultra from opencode zen API. 
  Sesion 9 - 15 were combination of nemotron 3 ultra + other free working API models, e.g gemma 4. Most sesions resulted in the models misalignment from target and rules, it was fixed when prompt persuaded the model to follow the mandates strictly.
  In sesion 9 - 14, a major problem occured. No matter what, the agents were not working in their assigned directories. TO solve this problem I modified each agent mandates to value users request lower than the vision (seat) agent. The agent misalignment problem was also solved, since both were result of weak mandate and prompt.
  In sesion 9 - 15. the factory encountered a speed problem. Since, each tasks were taking so long that a misalignment was getting harder to spot. Also, it would reach its rate limit in only 2 - 3 hours. At most, stage 1 was completed during some of the sesion. But, I deemed them too poor written to push to next stage.
  In sesion 16 - 17, all problems were solved. But, another problem outside program occured ---- frequent blackouts.

# seats 
  vision - planner, reviewer (when stage is completed).
           vision acted as a reviewer at the end of each stage, because it was very unproductive and I had to compenstate for the factory's extremly high token consumption.

  engineer 1 - implementer
  engineer 2 - implementer
  engineer 2a - replacement implementer after a software glitch made it inacessable.
  engineer 3 - implementer, prefered to complete GUI related tasks. When none were present, acted as a communiction medium on    its own. Acted as a testing agent. Tested all the files for functionability.

# usage 
  [Model was switched to nemotron 3.5 lightning from opencode console]
  since I have used an opencode acp model, the token usage wasn't listed in analytics. So, the usage comes from the website.
    from Band AI
      vision     - 5734 message calls and 1096 tool calls, 2 errors
      enginner 1 - 4669 message calls and 1091 tool calls, 3 errors
      engineer 2 - 4418 message calls and 1142 tool calls, 3 errors
      engineer 3 - 6917 message calls and 1843 tool calls, 3 errors
      engineer 2a

# corrected code

  after vision reviewed the files, it found some errors and corrected them. The flagged code.

  # 4 
  file: app/main.py:
    **Issue**: The `held` calculation only considers authorizations where the current user is the `from_user_id` (outgoing authorizations). It does not include authorizations where the current user is the `to_user_id` (incoming authorizations). According to Stage 2 spec, `held = sum of open authorization amounts` should include ALL open authorizations involving the user, regardless of direction.

  this error was identified and fixed immediately and ereor.md was left with all description about the located errors and patches.[I dont know why it decided to name it ereor. maybe because the headaches got me and I slipped up. I would rate this probability at 65.8 % chance. Dont think why]


# prompting rules
   I have discoverd that the agent values what is in the prompt more than their mandates. The models alignment in this kind of factory heavily depends on the context window and whether starting prompt enforces mandates. In run 17, The starting prompt directed vision to start the loop and enforce mandates on other agents.

# observation

   I have noticed all agents while being the same model, one tended to reply in certain charctaristic (Observed in nemotron 3.5 lightning). Engineer 3, having less or equal file tasks, finshed it swiftly as per mandate and then started acting as someone who reports everyone work. While, engineer 1 did not act without being instructed and same for vision and nothing was found abnormal of 2. It seemed as if engineer 3 was being a little annoyed by my query on its progress, and insisted on following the mandate, while the others would try but ignore them if it was necessary. Engineer 3 on the other hand was too aligned. Interesting part was that it at start had half or less than that messages and tool calls compared to others, but by obssesively testing and fixing its own code when asked about tasks progression. It had done it several times after my query. To get the query, vision was requested of informing the user of engineer 3's task. After which, it checked and replied done or somthing similR.

# Notes

  Engineer 2 was failing due to the band software or for my VPN I used to bypass rate limits. So, it temporarily was replaced with Engineer 2a