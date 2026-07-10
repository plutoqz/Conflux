<!-- source: https://en.wikipedia.org/wiki/Multi-agent_system -->
# Multi-agent system

> Source: https://en.wikipedia.org/wiki/Multi-agent_system
> License: CC BY-SA 4.0 (Wikipedia)

From Wikipedia, the free encyclopedia
System of multiple interacting agents

<!-- table omitted -->

Part of
a series
on
Multi-agent systems
Multi-agent simulation
- In computational economics
In computational economics
- In biology
In biology
- In social simulation
In social simulation
- Modeling software
Modeling software
Agent-oriented programming
- Auto-GPT
Auto-GPT
- Botnets
Botnets
- FIPA
FIPA
- Platforms for software agentsJADEJACKGORITE
Platforms for software agents
- JADE
JADE
- JACK
JACK
- GORITE
GORITE
- Software agent
Software agent
Related
- Distributed artificial intelligence
Distributed artificial intelligence
- Multi-agent pathfinding
Multi-agent pathfinding
- Multi-agent planning
Multi-agent planning
- Multi-agent reinforcement learning
Multi-agent reinforcement learning
- Self-propelled particles
Self-propelled particles
- Swarm robotics
Swarm robotics
- v
v
- t
t
- e
e
Simple reflex agent
Learning agent
Amulti-agent system(MAS) or "self-organized system" is a computational system composed of multiple interactingintelligent agents.[1][2][3]Multi-agent systems can solve problems that are difficult or impossible for an individual agent or amonolithic systemto solve.[4]Intelligence may includemethodic,functional,proceduralapproaches,algorithmicsearchorreinforcement learning.[5]With advancements inlarge language models(LLMs), LLM-based multi-agent systems have emerged as a new area of research, enabling more sophisticated interactions and coordination among agents.[6]

A
multi-agent system
(
MAS
) or "self-organized system" is a computational system composed of multiple interacting
intelligent agents
.
[
1
]
[
2
]
[
3
]
Multi-agent systems can solve problems that are difficult or impossible for an individual agent or a
monolithic system
to solve.
[
4
]
Intelligence may include
methodic
,
functional
,
procedural
approaches,
algorithmic
search
or
reinforcement learning
.
[
5
]
With advancements in
large language models
(LLMs), LLM-based multi-agent systems have emerged as a new area of research, enabling more sophisticated interactions and coordination among agents.
[
6
]
Despite considerable overlap, a multi-agent system is not always the same as anagent-based model(ABM).  The goal of an ABM is to search for explanatory insight into the collective behavior of agents (which do not necessarily need to be "intelligent") obeying simple rules, typically in natural systems, rather than in solving specific practical or engineering problems. The terminology of ABM tends to be used more often in the science, and MAS in engineering and technology.[7]Applications where multi-agent systems research may deliver an appropriate approach include online trading,[8]disaster response,[9][10]target surveillance[11]and social structure modelling.[12]

Despite considerable overlap, a multi-agent system is not always the same as an
agent-based model
(ABM).  The goal of an ABM is to search for explanatory insight into the collective behavior of agents (which do not necessarily need to be "intelligent") obeying simple rules, typically in natural systems, rather than in solving specific practical or engineering problems. The terminology of ABM tends to be used more often in the science, and MAS in engineering and technology.
[
7
]
Applications where multi-agent systems research may deliver an appropriate approach include online trading,
[
8
]
disaster response,
[
9
]
[
10
]
target surveillance
[
11
]
and social structure modelling.
[
12
]

## Concept

Concept
[
edit
]
Multi-agent systems consist of agents and theirenvironment. Typically, research on multi-agent systems refers tosoftware agents. However, the agents in a multi-agent system could equally well be robots, humans, or human teams, and may consist of combined human-agent teams.

Multi-agent systems consist of agents and their
environment
. Typically, research on multi-agent systems refers to
software agents
. However, the agents in a multi-agent system could equally well be robots, humans, or human teams, and may consist of combined human-agent teams.
Agents can be divided into types spanning simple to complex. Categories include:

Agents can be divided into types spanning simple to complex. Categories include:
- Passive agents[13]or "agent without goals" (such as obstacle, apple or key in any simple simulation)
Passive agents
[
13
]
or "agent without goals" (such as obstacle, apple or key in any simple simulation)
- Active agents[13]with simple goals (like birds in flocking, or wolf–sheep inprey-predator model)
Active agents
[
13
]
with simple goals (like birds in flocking, or wolf–sheep in
prey-predator model
)
- Cognitive agents, with beliefs, desires, intentions, and commitments processed by logical, probabilistic, and neural network-based reasoning
Cognitive agents, with beliefs, desires, intentions, and commitments processed by logical, probabilistic, and neural network-based reasoning
Agent environments can be divided into:

Agent environments can be divided into:
- Virtual
Virtual
- Discrete
Discrete
- Continuous
Continuous
Agent environments can also be organized according to properties such as accessibility (whether it is possible to gather complete information about the environment), determinism (whether an action causes a definite effect), dynamics (how many entities influence the environment in the moment), discreteness (whether the number of possible actions in the environment is finite), episodicity (whether agent actions in certain time periods influence other periods),[14]and dimensionality (whether spatial characteristics are important factors of the environment and the agent considers space in its decision making).[15]Agent actions are typically mediated via an appropriate middleware. This middleware offers a first-class design abstraction for multi-agent systems, providing means to govern resource access and agent coordination.[16]

Agent environments can also be organized according to properties such as accessibility (whether it is possible to gather complete information about the environment), determinism (whether an action causes a definite effect), dynamics (how many entities influence the environment in the moment), discreteness (whether the number of possible actions in the environment is finite), episodicity (whether agent actions in certain time periods influence other periods),
[
14
]
and dimensionality (whether spatial characteristics are important factors of the environment and the agent considers space in its decision making).
[
15
]
Agent actions are typically mediated via an appropriate middleware. This middleware offers a first-class design abstraction for multi-agent systems, providing means to govern resource access and agent coordination.
[
16
]

### Characteristics

Characteristics
[
edit
]
The agents in a multi-agent system have several important characteristics:[17]

The agents in a multi-agent system have several important characteristics:
[
17
]
- Autonomy: agents are at least partially independent, self-aware,autonomous
Autonomy: agents are at least partially independent, self-aware,
autonomous
- Local views: no agent has a full global view, or the system is too complex for an agent to exploit such knowledge
Local views: no agent has a full global view, or the system is too complex for an agent to exploit such knowledge
- Decentralization: no agent is designated as controlling (or the system is effectively reduced to a monolithic system)[18]
Decentralization: no agent is designated as controlling (or the system is effectively reduced to a monolithic system)
[
18
]

### Self-organisation and self-direction

Self-organisation and self-direction
[
edit
]
Multi-agent systems can manifestself-organisationas well as self-direction and othercontrol paradigmsand related complex behaviors even when the individual strategies of all their agents are simple.[citation needed]When agents can share knowledge using any agreed language, within the constraints of the system's communication protocol, the approach may lead to a common improvement. Example languages areKnowledge Query Manipulation Language(KQML) orAgent Communication Language(ACL).

Multi-agent systems can manifest
self-organisation
as well as self-direction and other
control paradigms
and related complex behaviors even when the individual strategies of all their agents are simple.
[
citation needed
]
When agents can share knowledge using any agreed language, within the constraints of the system's communication protocol, the approach may lead to a common improvement. Example languages are
Knowledge Query Manipulation Language
(KQML) or
Agent Communication Language
(ACL).

### Decision-Making

Decision-Making
[
edit
]
Decision protocols in multi-agent systems refer to the structured rules and procedures that agents follow to reach collective decisions or agreements. Such protocols specify how agents share information, negotiate, and resolve conflicts, ensuring coordinated behavior and effective joint actions. Decision protocols can range fromvotingmechanisms toconsensus-building algorithms, and they significantly influence the efficiency and reliability of multi-agent interactions.[19]

Decision protocols in multi-agent systems refer to the structured rules and procedures that agents follow to reach collective decisions or agreements. Such protocols specify how agents share information, negotiate, and resolve conflicts, ensuring coordinated behavior and effective joint actions. Decision protocols can range from
voting
mechanisms to
consensus
-building algorithms, and they significantly influence the efficiency and reliability of multi-agent interactions.
[
19
]

### System paradigms

System paradigms
[
edit
]
Many MAS are implemented in computer simulations, stepping the system through discrete "time steps". The MAS components communicate typically using a weighted request matrix, e.g.

Many MAS are implemented in computer simulations, stepping the system through discrete "time steps". The MAS components communicate typically using a weighted request matrix, e.g.

```
Speed-VERY_IMPORTANT: min=45 mph, 
 Path length-MEDIUM_IMPORTANCE: max=60 expectedMax=40, 
 Max-Weight-UNIMPORTANT 
 Contract Priority-REGULAR
```

Speed-VERY_IMPORTANT: min=45 mph, 
 Path length-MEDIUM_IMPORTANCE: max=60 expectedMax=40, 
 Max-Weight-UNIMPORTANT 
 Contract Priority-REGULAR
and a weighted response matrix, e.g.

and a weighted response matrix, e.g.

```
Speed-min:50 but only if weather sunny, 
 Path length:25 for sunny / 46 for rainy
 Contract Priority-REGULAR
 note – ambulance will override this priority and you'll have to wait
```

Speed-min:50 but only if weather sunny, 
 Path length:25 for sunny / 46 for rainy
 Contract Priority-REGULAR
 note – ambulance will override this priority and you'll have to wait
A challenge-response-contract scheme is common in MAS systems, where

A challenge-response-contract scheme is common in MAS systems, where
- First a"Who can?"question is distributed.
First a
"
Who can?
"
question is distributed.
- Only the relevant components respond:"I can, at this price".
Only the relevant components respond:
"
I can, at this price
"
.
- Finally, a contract is set up, usually in several short communication steps between sides,
Finally, a contract is set up, usually in several short communication steps between sides,
also considering other components, evolving "contracts" and the restriction sets of the component algorithms.

also considering other components, evolving "contracts" and the restriction sets of the component algorithms.
Another paradigm commonly used with MAS is the "pheromone", where components leave information for other nearby components. These pheromones may evaporate/concentrate with time, that is their values may decrease (or increase).

Another paradigm commonly used with MAS is the "
pheromone
", where components leave information for other nearby components. These pheromones may evaporate/concentrate with time, that is their values may decrease (or increase).

### Properties

Properties
[
edit
]
MAS tend to find the best solution for their problems without intervention. There is high similarity here to physical phenomena, such as energy minimizing, where physical objects tend to reach the lowest energy possible within the physically constrained world. For example: many of the cars entering a metropolis in the morning will be available for leaving that same metropolis in the evening.

MAS tend to find the best solution for their problems without intervention. There is high similarity here to physical phenomena, such as energy minimizing, where physical objects tend to reach the lowest energy possible within the physically constrained world. For example: many of the cars entering a metropolis in the morning will be available for leaving that same metropolis in the evening.
The systems also tend to prevent propagation of faults, self-recover and be fault tolerant, mainly due to the redundancy of components.

The systems also tend to prevent propagation of faults, self-recover and be fault tolerant, mainly due to the redundancy of components.

## Research

Research
[
edit
]
The study of multi-agent systems is "concerned with the development and analysis of sophisticatedAIproblem-solving and control architectures for both single-agent and multiple-agent systems."[20]Research topics include:

The study of multi-agent systems is "concerned with the development and analysis of sophisticated
AI
problem-solving and control architectures for both single-agent and multiple-agent systems."
[
20
]
Research topics include:
- agent-oriented software engineering
agent-oriented software engineering
- beliefs, desires, and intentions (BDI)
beliefs, desires, and intentions (
BDI
)
- cooperation and coordination
cooperation and coordination
- distributed constraint optimization(DCOPs)
distributed constraint optimization
(DCOPs)
- organization
organization
- communication
communication
- negotiation
negotiation
- distributed problem solving
distributed problem solving
- multi-agent learning[21]
multi-agent learning
[
21
]
- agent mining
agent mining
- scientific communities (e.g., on biological flocking, language evolution, and economics)[22][23]
scientific communities (e.g., on biological flocking, language evolution, and economics)
[
22
]
[
23
]
- dependability and fault-tolerance
dependability and fault-tolerance
- robotics,[24]multi-robot systems (MRS), robotic clusters
robotics,
[
24
]
multi-robot systems (MRS), robotic clusters
- multi-agent systems also present possible applications in microrobotics,[25]where the physical interaction between the agents are exploited to perform complex tasks such as manipulation and assembly of passive components.
multi-agent systems also present possible applications in microrobotics,
[
25
]
where the physical interaction between the agents are exploited to perform complex tasks such as manipulation and assembly of passive components.
- language model-based multi-agent systems[6]
language model-based multi-agent systems
[
6
]
A MAS involves more than just the design of an intelligent system. It 
also provides insights and understanding about interactions among humans, as 
they organize themselves into various groups, committees, societies, and 
economies in order to improve their lives. For example, economists have been 
studying multiple agents for more than two hundred years, ever since Adam 
Smith in the eighteenth century, with the goal of being able to understand and 
predict economies. Economics provides ways to characterize masses of agents. 
and these are useful for DAI. But in return, DAI provides a means to construct 
artificial economies that can test economists’ theories before, rather than after, 
they are applied.

A MAS involves more than just the design of an intelligent system. It 
also provides insights and understanding about interactions among humans, as 
they organize themselves into various groups, committees, societies, and 
economies in order to improve their lives. For example, economists have been 
studying multiple agents for more than two hundred years, ever since Adam 
Smith in the eighteenth century, with the goal of being able to understand and 
predict economies. Economics provides ways to characterize masses of agents. 
and these are useful for DAI. But in return, DAI provides a means to construct 
artificial economies that can test economists’ theories before, rather than after, 
they are applied.

## Frameworks

Frameworks
[
edit
]
See also:
CrewAI
Frameworks have emerged that implement common standards (such as theFIPAandOMGMASIF standards).[26]These frameworks e.g.JADE, save time and aid in the standardization of MAS development.[27]

Frameworks have emerged that implement common standards (such as the
FIPA
and
OMG
MASIF standards).
[
26
]
These frameworks e.g.
JADE
, save time and aid in the standardization of MAS development.
[
27
]
Currently though, no standard is actively maintained from FIPA or OMG. Efforts for further development of software agents in industrial context are carried out inIEEEIES technical committee on Industrial Agents.[28]

Currently though, no standard is actively maintained from FIPA or OMG. Efforts for further development of software agents in industrial context are carried out in
IEEE
IES technical committee on Industrial Agents.
[
28
]
With advancements inlarge language models(LLMs) such asChatGPT, LLM-based multi-agent frameworks, such as CAMEL,[29][6]have emerged as a new paradigm for developing multi-agent applications. Recent work has shown that such debate-oriented systems vary in their orchestration (e.g., discussion paradigms[30]). The MALLM framework is used to systematically evaluate possible configurations of frameworks.[31]

With advancements in
large language models
(LLMs) such as
ChatGPT
, LLM-based multi-agent frameworks, such as CAMEL,
[
29
]
[
6
]
have emerged as a new paradigm for developing multi-agent applications. Recent work has shown that such debate-oriented systems vary in their orchestration (e.g., discussion paradigms
[
30
]
). The MALLM framework is used to systematically evaluate possible configurations of frameworks.
[
31
]

## Applications

Applications
[
edit
]
MAS have not only been applied in academic research, but also in industry.[32]MAS are applied in the real world to graphical applications such as computer games. Agent systems have been used in films.[33]It is widely advocated for use in networking and mobile technologies, to achieve automatic and dynamic load balancing, high scalability and self-healing networks. They are being used for coordinated defence systems.

MAS have not only been applied in academic research, but also in industry.
[
32
]
MAS are applied in the real world to graphical applications such as computer games. Agent systems have been used in films.
[
33
]
It is widely advocated for use in networking and mobile technologies, to achieve automatic and dynamic load balancing, high scalability and self-healing networks. They are being used for coordinated defence systems.
Other applications[34]includetransportation,[35]logistics,[36]graphics, manufacturing,power system,[37]smartgrids,[38]and theGIS.

Other applications
[
34
]
include
transportation
,
[
35
]
logistics,
[
36
]
graphics, manufacturing,
power system
,
[
37
]
smartgrids
,
[
38
]
and the
GIS
.
Also,Multi-agent Systems Artificial Intelligence(MAAI) are used for simulating societies, the purpose thereof being helpful in the fields of climate, energy,epidemiology,conflict management, child abuse, ....[39]

Also,
Multi-agent Systems Artificial Intelligence
(MAAI) are used for simulating societies, the purpose thereof being helpful in the fields of climate, energy,
epidemiology
,
conflict management
, child abuse, ....
[
39
]
Some organisations working on using multi-agent system models include Center for Modelling Social Systems,[40]Centre for Research in Social Simulation,[41]Centre for Policy Modelling, Society for Modelling and Simulation International.[39]

Some organisations working on using multi-agent system models include Center for Modelling Social Systems,
[
40
]
Centre for Research in Social Simulation,
[
41
]
Centre for Policy Modelling, Society for Modelling and Simulation International.
[
39
]
Vehicular traffic with controlled autonomous vehicles can be modelling as a multi-agent system involving crowd dynamics.[42]

Vehicular traffic with controlled autonomous vehicles can be modelling as a multi-agent system involving crowd dynamics.
[
42
]
Hallerbach et al. discussed the application of agent-based approaches for the development and validation ofautomated driving systemsvia a digital twin of the vehicle-under-test and microscopic traffic simulation based on independent agents.[43]Waymohas created a multi-agent simulation environment Carcraft to test algorithms forself-driving cars.[44][45]It simulates traffic interactions between human drivers, pedestrians and automated vehicles. People's behavior is imitated by artificial agents based on data of real human behavior.

Hallerbach et al. discussed the application of agent-based approaches for the development and validation of
automated driving systems
via a digital twin of the vehicle-under-test and microscopic traffic simulation based on independent agents.
[
43
]
Waymo
has created a multi-agent simulation environment Carcraft to test algorithms for
self-driving cars
.
[
44
]
[
45
]
It simulates traffic interactions between human drivers, pedestrians and automated vehicles. People's behavior is imitated by artificial agents based on data of real human behavior.

## See also

See also
[
edit
]
- Comparison of agent-based modeling software
Comparison of agent-based modeling software
- Agent-based computational economics(ACE)
Agent-based computational economics
(ACE)
- Artificial brain
Artificial brain
- Artificial intelligence
Artificial intelligence
- Artificial life
Artificial life
- AI mayor
AI mayor
- Black box
Black box
- Blackboard system
Blackboard system
- Complex systems
Complex systems
- Discrete event simulation
Discrete event simulation
- Distributed artificial intelligence
Distributed artificial intelligence
- Emergence
Emergence
- Evolutionary computation
Evolutionary computation
- Friendly artificial intelligence
Friendly artificial intelligence
- Game theory
Game theory
- Hallucination (artificial intelligence)
Hallucination (artificial intelligence)
- Human-based genetic algorithm
Human-based genetic algorithm
- Hybrid intelligent system
Hybrid intelligent system
- Knowledge Query and Manipulation Language(KQML)
Knowledge Query and Manipulation Language
(KQML)
- Microbial intelligence
Microbial intelligence
- Multi-agent planning
Multi-agent planning
- Multi-agent reinforcement learning
Multi-agent reinforcement learning
- Pattern-oriented modeling
Pattern-oriented modeling
- PlatBox Project
PlatBox Project
- Reinforcement learning
Reinforcement learning
- Scientific community metaphor
Scientific community metaphor
- Self-reconfiguring modular robot
Self-reconfiguring modular robot
- Simulated reality
Simulated reality
- Social simulation
Social simulation
- Software agent
Software agent
- Software bot
Software bot
- Swarm intelligence
Swarm intelligence
- Swarm robotics
Swarm robotics

## References

References
[
edit
]
- ^Su, Yu-Hsiang; Arvin, Farshad; Hu, Junyan (2026). "Safety-Critical Multi-Agent Flocking via Motion-Aware Control Barrier Functions".IEEE Transactions on Automation Science and Engineering.23:10506–10520.doi:10.1109/TASE.2026.3695359.
^
Su, Yu-Hsiang; Arvin, Farshad; Hu, Junyan (2026). "Safety-Critical Multi-Agent Flocking via Motion-Aware Control Barrier Functions".
IEEE Transactions on Automation Science and Engineering
.
23
:
10506–
10520.
doi
:
10.1109/TASE.2026.3695359
.
- ^Singh, Munindar P. (1994).Multiagent Systems: A Theoretical Framework for Intentions, Know-How, and Communications. Vol. 799. Springer-Verlag, Lecture Notes in Computer Science.ISBN0-387-58026-3.
^
Singh, Munindar P. (1994).
Multiagent Systems: A Theoretical Framework for Intentions, Know-How, and Communications
. Vol. 799. Springer-Verlag, Lecture Notes in Computer Science.
ISBN
0-387-58026-3
.
- ^Yoav Shoham, Kevin Leyton-Brown.Multiagent Systems: Algorithmic, Game-Theoretic, and Logical Foundations.Cambridge University Press, 2009.http://www.masfoundations.org/
^
Yoav Shoham, Kevin Leyton-Brown.
Multiagent Systems: Algorithmic, Game-Theoretic, and Logical Foundations.
Cambridge University Press, 2009.
http://www.masfoundations.org/
- ^H. Pan; M. Zahmatkesh; F. Rekabi-Bana; F. Arvin; J. Hu "T-STAR: Time-Optimal Swarm Trajectory Planning for Quadrotor Unmanned Aerial Vehicles" IEEE Transactions on Intelligent Transportation Systems, 2025.
^
H. Pan; M. Zahmatkesh; F. Rekabi-Bana; F. Arvin; J. Hu "
T-STAR: Time-Optimal Swarm Trajectory Planning for Quadrotor Unmanned Aerial Vehicles
" IEEE Transactions on Intelligent Transportation Systems, 2025.
- ^Stefano V. Albrecht, Filippos Christianos, Lukas Schäfer.Multi-Agent Reinforcement Learning: Foundations and Modern Approaches.MIT Press, 2024.https://www.marl-book.com/
^
Stefano V. Albrecht, Filippos Christianos, Lukas Schäfer.
Multi-Agent Reinforcement Learning: Foundations and Modern Approaches.
MIT Press, 2024.
https://www.marl-book.com/
- ^abcLi, Guohao (2023)."Camel: Communicative agents for "mind" exploration of large language model society"(PDF).Advances in Neural Information Processing Systems.36:51991–52008.arXiv:2303.17760.S2CID257900712.
^
a
b
c
Li, Guohao (2023).
"Camel: Communicative agents for "mind" exploration of large language model society"
(PDF)
.
Advances in Neural Information Processing Systems
.
36
:
51991–
52008.
arXiv
:
2303.17760
.
S2CID
257900712
.
- ^Niazi, Muaz; Hussain, Amir (2011)."Agent-based Computing from Multi-agent Systems to Agent-Based Models: A Visual Survey"(PDF).Scientometrics.89(2):479–499.arXiv:1708.05872.doi:10.1007/s11192-011-0468-9.hdl:1893/3378.S2CID17934527.
^
Niazi, Muaz; Hussain, Amir (2011).
"Agent-based Computing from Multi-agent Systems to Agent-Based Models: A Visual Survey"
(PDF)
.
Scientometrics
.
89
(2):
479–
499.
arXiv
:
1708.05872
.
doi
:
10.1007/s11192-011-0468-9
.
hdl
:
1893/3378
.
S2CID
17934527
.
- ^Rogers, Alex; David, E.; Schiff, J.; Jennings, N.R. (2007)."The Effects of Proxy Bidding and Minimum Bid Increments within eBay Auctions".ACM Transactions on the Web.1(2): 9–es.CiteSeerX10.1.1.65.4539.doi:10.1145/1255438.1255441.S2CID207163424. Archived fromthe originalon April 2, 2010. RetrievedMarch 18,2008.
^
Rogers, Alex; David, E.; Schiff, J.; Jennings, N.R. (2007).
"The Effects of Proxy Bidding and Minimum Bid Increments within eBay Auctions"
.
ACM Transactions on the Web
.
1
(2): 9–es.
CiteSeerX
10.1.1.65.4539
.
doi
:
10.1145/1255438.1255441
.
S2CID
207163424
. Archived from
the original
on April 2, 2010
. Retrieved
March 18,
2008
.
- ^Schurr, Nathan; Marecki, Janusz; Tambe, Milind; Scerri, Paul; Kasinadhuni, Nikhil; Lewis, J.P. (2005)."The Future of Disaster Response: Humans Working with Multiagent Teams using DEFACTO".Archived(PDF)from the original on June 3, 2013. RetrievedJanuary 8,2024.
^
Schurr, Nathan; Marecki, Janusz; Tambe, Milind; Scerri, Paul; Kasinadhuni, Nikhil; Lewis, J.P. (2005).
"The Future of Disaster Response: Humans Working with Multiagent Teams using DEFACTO"
.
Archived
(PDF)
from the original on June 3, 2013
. Retrieved
January 8,
2024
.
- ^Genc, Zulkuf; et al. (2013)."Agent-Based Information Infrastructure for Disaster Management"(PDF).Intelligent Systems for Crisis Management. Lecture Notes in Geoinformation and Cartography. pp.349–355.doi:10.1007/978-3-642-33218-0_26.ISBN978-3-642-33217-3.
^
Genc, Zulkuf; et al. (2013).
"Agent-Based Information Infrastructure for Disaster Management"
(PDF)
.
Intelligent Systems for Crisis Management
. Lecture Notes in Geoinformation and Cartography. pp.
349–
355.
doi
:
10.1007/978-3-642-33218-0_26
.
ISBN
978-3-642-33217-3
.
- ^Hu, Junyan; Bhowmick, Parijat; Lanzon, Alexander (2020)."Distributed Adaptive Time-Varying Group Formation Tracking for Multiagent Systems With Multiple Leaders on Directed Graphs".IEEE Transactions on Control of Network Systems.7:140–150.doi:10.1109/TCNS.2019.2913619.S2CID149609966.
^
Hu, Junyan; Bhowmick, Parijat; Lanzon, Alexander (2020).
"Distributed Adaptive Time-Varying Group Formation Tracking for Multiagent Systems With Multiple Leaders on Directed Graphs"
.
IEEE Transactions on Control of Network Systems
.
7
:
140–
150.
doi
:
10.1109/TCNS.2019.2913619
.
S2CID
149609966
.
- ^Sun, Ron; Naveh, Isaac (June 30, 2004)."Simulating Organizational Decision-Making Using a Cognitively Realistic Agent Model".Journal of Artificial Societies and Social Simulation.
^
Sun, Ron
; Naveh, Isaac (June 30, 2004).
"Simulating Organizational Decision-Making Using a Cognitively Realistic Agent Model"
.
Journal of Artificial Societies and Social Simulation
.
- ^abKubera, Yoann; Mathieu, Philippe; Picault, Sébastien (2010),"Everything can be Agent!"(PDF),Proceedings of the Ninth International Joint Conference on Autonomous Agents and Multi-Agent Systems (AAMAS'2010):1547–1548
^
a
b
Kubera, Yoann; Mathieu, Philippe; Picault, Sébastien (2010),
"Everything can be Agent!"
(PDF)
,
Proceedings of the Ninth International Joint Conference on Autonomous Agents and Multi-Agent Systems (AAMAS'2010)
:
1547–
1548
- ^Russell, Stuart J.;Norvig, Peter(2003),Artificial Intelligence: A Modern Approach(2nd ed.), Upper Saddle River, New Jersey: Prentice Hall,ISBN0-13-790395-2
^
Russell, Stuart J.
;
Norvig, Peter
(2003),
Artificial Intelligence: A Modern Approach
(2nd ed.), Upper Saddle River, New Jersey: Prentice Hall,
ISBN
0-13-790395-2
- ^Salamon, Tomas (2011).Design of Agent-Based Models. Repin: Bruckner Publishing. p. 22.ISBN978-80-904661-1-1.
^
Salamon, Tomas (2011).
Design of Agent-Based Models
. Repin: Bruckner Publishing. p. 22.
ISBN
978-80-904661-1-1
.
- ^Weyns, Danny; Omicini, Amdrea; Odell, James (2007). "Environment as a first-class abstraction in multiagent systems".Autonomous Agents and Multi-Agent Systems.14(1):5–30.CiteSeerX10.1.1.154.4480.doi:10.1007/s10458-006-0012-0.S2CID13347050.
^
Weyns, Danny; Omicini, Amdrea; Odell, James (2007). "Environment as a first-class abstraction in multiagent systems".
Autonomous Agents and Multi-Agent Systems
.
14
(1):
5–
30.
CiteSeerX
10.1.1.154.4480
.
doi
:
10.1007/s10458-006-0012-0
.
S2CID
13347050
.
- ^Wooldridge, Michael (2002).An Introduction to MultiAgent Systems.John Wiley & Sons. p. 366.ISBN978-0-471-49691-5.
^
Wooldridge, Michael (2002).
An Introduction to MultiAgent Systems
.
John Wiley & Sons
. p. 366.
ISBN
978-0-471-49691-5
.
- ^Panait, Liviu; Luke, Sean (2005)."Cooperative Multi-Agent Learning: The State of the Art"(PDF).Autonomous Agents and Multi-Agent Systems.11(3):387–434.CiteSeerX10.1.1.307.6671.doi:10.1007/s10458-005-2631-2.S2CID19706.
^
Panait, Liviu; Luke, Sean (2005).
"Cooperative Multi-Agent Learning: The State of the Art"
(PDF)
.
Autonomous Agents and Multi-Agent Systems
.
11
(3):
387–
434.
CiteSeerX
10.1.1.307.6671
.
doi
:
10.1007/s10458-005-2631-2
.
S2CID
19706
.
- ^Kaesberg, Lars Benedikt; Becker, Jonas; Wahle, Jan Philip; Ruas, Terry; Gipp, Bela (July 1, 2025). Che, Wanxiang; Nabende, Joyce; Shutova, Ekaterina; Pilehvar, Mohammad Taher (eds.)."Voting or Consensus? Decision-Making in Multi-Agent Debate".Findings of the Association for Computational Linguistics: ACL 2025. Vienna, Austria: Association for Computational Linguistics:11640–11671.arXiv:2502.19130.doi:10.18653/v1/2025.findings-acl.606.ISBN979-8-89176-256-5.{{cite journal}}:  CS1 maint: year (link)
^
Kaesberg, Lars Benedikt; Becker, Jonas; Wahle, Jan Philip; Ruas, Terry; Gipp, Bela (July 1, 2025). Che, Wanxiang; Nabende, Joyce; Shutova, Ekaterina; Pilehvar, Mohammad Taher (eds.).
"Voting or Consensus? Decision-Making in Multi-Agent Debate"
.
Findings of the Association for Computational Linguistics: ACL 2025
. Vienna, Austria: Association for Computational Linguistics:
11640–
11671.
arXiv
:
2502.19130
.
doi
:
10.18653/v1/2025.findings-acl.606
.
ISBN
979-8-89176-256-5
.

```
{{cite journal}}
```

{{
cite journal
}}
:  CS1 maint: year (
link
)
- ^"The Multi-Agent Systems Lab".University of Massachusetts Amherst. RetrievedOctober 16,2009.
^
"The Multi-Agent Systems Lab"
.
University of Massachusetts Amherst
. Retrieved
October 16,
2009
.
- ^Albrecht, Stefano; Stone, Peter (2017), "Multiagent Learning: Foundations and Recent Trends. Tutorial",IJCAI-17 conference(PDF)
^
Albrecht, Stefano; Stone, Peter (2017), "Multiagent Learning: Foundations and Recent Trends. Tutorial",
IJCAI-17 conference
(PDF)
- ^Cucker, Felipe;Steve Smale(2007)."The Mathematics of Emergence"(PDF).Japanese Journal of Mathematics.2:197–227.doi:10.1007/s11537-007-0647-x.S2CID2637067. RetrievedJune 9,2008.
^
Cucker, Felipe;
Steve Smale
(2007).
"The Mathematics of Emergence"
(PDF)
.
Japanese Journal of Mathematics
.
2
:
197–
227.
doi
:
10.1007/s11537-007-0647-x
.
S2CID
2637067
. Retrieved
June 9,
2008
.
- ^Shen, Jackie (Jianhong) (2008)."Cucker–Smale Flocking under Hierarchical Leadership".SIAM J. Appl. Math.68(3):694–719.arXiv:q-bio/0610048.doi:10.1137/060673254.S2CID14655317. RetrievedJune 9,2008.
^
Shen, Jackie (Jianhong) (2008).
"Cucker–Smale Flocking under Hierarchical Leadership"
.
SIAM J. Appl. Math
.
68
(3):
694–
719.
arXiv
:
q-bio/0610048
.
doi
:
10.1137/060673254
.
S2CID
14655317
. Retrieved
June 9,
2008
.
- ^Ahmed, S.; Karsiti, M.N. (2007), "A testbed for control schemes using multi agent nonholonomic robots",2007 IEEE International Conference on Electro/Information Technology, p. 459,doi:10.1109/EIT.2007.4374547,ISBN978-1-4244-0940-2,S2CID2734931
^
Ahmed, S.; Karsiti, M.N. (2007), "A testbed for control schemes using multi agent nonholonomic robots",
2007 IEEE International Conference on Electro/Information Technology
, p. 459,
doi
:
10.1109/EIT.2007.4374547
,
ISBN
978-1-4244-0940-2
,
S2CID
2734931
- ^Yang, Lidong; Li, Zhang (2021). "Motion control in magnetic microrobotics: From individual and multiple robots to swarms".Annual Review of Control, Robotics, and Autonomous Systems.4:509–534.doi:10.1146/annurev-control-032720-104318.S2CID228892228.
^
Yang, Lidong; Li, Zhang (2021). "Motion control in magnetic microrobotics: From individual and multiple robots to swarms".
Annual Review of Control, Robotics, and Autonomous Systems
.
4
:
509–
534.
doi
:
10.1146/annurev-control-032720-104318
.
S2CID
228892228
.
- ^"OMG Document – orbos/97-10-05 (Update of Revised MAF Submission)".www.omg.org. RetrievedFebruary 19,2019.
^
"OMG Document – orbos/97-10-05 (Update of Revised MAF Submission)"
.
www.omg.org
. Retrieved
February 19,
2019
.
- ^Ahmed, Salman; Karsiti, Mohd N.; Agustiawan, Herman (2007)."A development framework for collaborative robots using feedback control". RetrievedJanuary 8,2024.
^
Ahmed, Salman; Karsiti, Mohd N.; Agustiawan, Herman (2007).
"A development framework for collaborative robots using feedback control"
. Retrieved
January 8,
2024
.
- ^"IEEE IES Technical Committee on Industrial Agents (TC-IA)".tcia.ieee-ies.org. RetrievedFebruary 19,2019.
^
"IEEE IES Technical Committee on Industrial Agents (TC-IA)"
.
tcia.ieee-ies.org
. Retrieved
February 19,
2019
.
- ^"CAMEL: Finding the Scaling Law of Agents. The first and the best multi-agent framework".GitHub.
^
"CAMEL: Finding the Scaling Law of Agents. The first and the best multi-agent framework"
.
GitHub
.
- ^Yin, Zhangyue; Sun, Qiushi; Chang, Cheng; Guo, Qipeng; Dai, Junqi; Huang, Xuanjing; Qiu, Xipeng (December 2023)."Exchange‑of‑Thought: Enhancing Large Language Model Capabilities through Cross‑Model Communication".Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing. Singapore: Association for Computational Linguistics. pp.15135–15153.doi:10.18653/v1/2023.emnlp-main.936.
^
Yin, Zhangyue; Sun, Qiushi; Chang, Cheng; Guo, Qipeng; Dai, Junqi; Huang, Xuanjing; Qiu, Xipeng (December 2023).
"Exchange‑of‑Thought: Enhancing Large Language Model Capabilities through Cross‑Model Communication"
.
Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing
. Singapore: Association for Computational Linguistics. pp.
15135–
15153.
doi
:
10.18653/v1/2023.emnlp-main.936
.
- ^Becker, Jonas; Kaesberg, Lars Benedikt; Bauer, Niklas; Wahle, Jan Philip; Ruas, Terry; Gipp, Bela (November 2025)."MALLM: Multi‑Agent Large Language Models Framework".Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing: System Demonstrations. Suzhou, China: Association for Computational Linguistics. pp.418–439.doi:10.18653/v1/2025.emnlp-demos.29.
^
Becker, Jonas; Kaesberg, Lars Benedikt; Bauer, Niklas; Wahle, Jan Philip; Ruas, Terry; Gipp, Bela (November 2025).
"MALLM: Multi‑Agent Large Language Models Framework"
.
Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing: System Demonstrations
. Suzhou, China: Association for Computational Linguistics. pp.
418–
439.
doi
:
10.18653/v1/2025.emnlp-demos.29
.
- ^Leitão, Paulo; Karnouskos, Stamatis (March 26, 2015).Industrial agents : emerging applications of software agents in industry. Leitão, Paulo,, Karnouskos, Stamatis. Amsterdam, Netherlands.ISBN978-0128003411.OCLC905853947.{{cite book}}:  CS1 maint: location missing publisher (link)
^
Leitão, Paulo; Karnouskos, Stamatis (March 26, 2015).
Industrial agents : emerging applications of software agents in industry
. Leitão, Paulo,, Karnouskos, Stamatis. Amsterdam, Netherlands.
ISBN
978-0128003411
.
OCLC
905853947
.

```
{{cite book}}
```

{{
cite book
}}
:  CS1 maint: location missing publisher (
link
)
- ^"Film showcase".MASSIVE. RetrievedApril 28,2012.
^
"Film showcase"
.
MASSIVE
. Retrieved
April 28,
2012
.
- ^Leitao, Paulo; Karnouskos, Stamatis; Ribeiro, Luis; Lee, Jay; Strasser, Thomas; Colombo, Armando W. (2016)."Smart Agents in Industrial Cyber–Physical Systems".Proceedings of the IEEE.104(5):1086–1101.doi:10.1109/JPROC.2016.2521931.hdl:10198/15438.ISSN0018-9219.S2CID579475.
^
Leitao, Paulo; Karnouskos, Stamatis; Ribeiro, Luis; Lee, Jay; Strasser, Thomas; Colombo, Armando W. (2016).
"Smart Agents in Industrial Cyber–Physical Systems"
.
Proceedings of the IEEE
.
104
(5):
1086–
1101.
doi
:
10.1109/JPROC.2016.2521931
.
hdl
:
10198/15438
.
ISSN
0018-9219
.
S2CID
579475
.
- ^Xiao-Feng Xie, S. Smith, G. Barlow.Schedule-driven coordination for real-time traffic network control. International Conference on Automated Planning and Scheduling (ICAPS), São Paulo, Brazil, 2012: 323–331.
^
Xiao-Feng Xie, S. Smith, G. Barlow.
Schedule-driven coordination for real-time traffic network control
. International Conference on Automated Planning and Scheduling (ICAPS), São Paulo, Brazil, 2012: 323–331.
- ^Máhr, T. S.; Srour, J.; De Weerdt, M.; Zuidwijk, R. (2010). "Can agents measure up? A comparative study of an agent-based and on-line optimization approach for a drayage problem with uncertainty".Transportation Research Part C: Emerging Technologies.18(1):99–119.Bibcode:2010TRPC...18...99M.CiteSeerX10.1.1.153.770.doi:10.1016/j.trc.2009.04.018.
^
Máhr, T. S.; Srour, J.; De Weerdt, M.; Zuidwijk, R. (2010). "Can agents measure up? A comparative study of an agent-based and on-line optimization approach for a drayage problem with uncertainty".
Transportation Research Part C: Emerging Technologies
.
18
(1):
99–
119.
Bibcode
:
2010TRPC...18...99M
.
CiteSeerX
10.1.1.153.770
.
doi
:
10.1016/j.trc.2009.04.018
.
- ^Kazemi, Hamidreza; Liasi, Sahand; Sheikh-El-Eslami, Mohammadkazem (November 2018)."Generation Expansion Planning Considering Investment Dynamic of Market Participants Using Multi-agent System".2018 Smart Grid Conference (SGC). pp.1–6.doi:10.1109/SGC.2018.8777904.ISBN978-1-7281-1138-4. RetrievedJanuary 8,2024.
^
Kazemi, Hamidreza; Liasi, Sahand; Sheikh-El-Eslami, Mohammadkazem (November 2018).
"Generation Expansion Planning Considering Investment Dynamic of Market Participants Using Multi-agent System"
.
2018 Smart Grid Conference (SGC)
. pp.
1–
6.
doi
:
10.1109/SGC.2018.8777904
.
ISBN
978-1-7281-1138-4
. Retrieved
January 8,
2024
.
- ^Singh, Vijay; Samuel, Paulson (June 6, 2017)."Distributed Multi -Agent System Based Load Frequency Control for Multi- Area Power System in Smart Grid".IEEE Transactions on Industrial Electronics.64(6):5151–5160.doi:10.1109/TIE.2017.2668983. RetrievedJanuary 8,2024.
^
Singh, Vijay; Samuel, Paulson (June 6, 2017).
"Distributed Multi -Agent System Based Load Frequency Control for Multi- Area Power System in Smart Grid"
.
IEEE Transactions on Industrial Electronics
.
64
(6):
5151–
5160.
doi
:
10.1109/TIE.2017.2668983
. Retrieved
January 8,
2024
.
- ^ab"AI can predict your future behaviour with powerful new simulations".New Scientist.
^
a
b
"AI can predict your future behaviour with powerful new simulations"
.
New Scientist
.
- ^"Center for Modeling Social Systems - Norce".NORCE Norwegian Research Centre. RetrievedApril 13,2025.
^
"Center for Modeling Social Systems - Norce"
.
NORCE Norwegian Research Centre
. Retrieved
April 13,
2025
.
- ^"Centre for Research in Social Simulation – A multidisciplinary centre bringing together the social sciences and agent-based modelling to promote and support the use of social simulation in research in the human sciences". RetrievedApril 13,2025.
^
"Centre for Research in Social Simulation – A multidisciplinary centre bringing together the social sciences and agent-based modelling to promote and support the use of social simulation in research in the human sciences"
. Retrieved
April 13,
2025
.
- ^Gong, Xiaoqian; Herty, Michael; Piccoli, Benedetto; Visconti, Giuseppe (May 3, 2023)."Crowd Dynamics: Modeling and Control of Multiagent Systems".Annual Review of Control, Robotics, and Autonomous Systems.6(1):261–282.doi:10.1146/annurev-control-060822-123629.ISSN2573-5144.
^
Gong, Xiaoqian; Herty, Michael; Piccoli, Benedetto; Visconti, Giuseppe (May 3, 2023).
"Crowd Dynamics: Modeling and Control of Multiagent Systems"
.
Annual Review of Control, Robotics, and Autonomous Systems
.
6
(1):
261–
282.
doi
:
10.1146/annurev-control-060822-123629
.
ISSN
2573-5144
.
- ^Hallerbach, S.; Xia, Y.; Eberle, U.; Koester, F. (2018)."Simulation-Based Identification of Critical Scenarios for Cooperative and Automated Vehicles".SAE International Journal of Connected and Automated Vehicles.1(2). SAE International: 93.doi:10.4271/2018-01-1066.
^
Hallerbach, S.; Xia, Y.; Eberle, U.; Koester, F. (2018).
"Simulation-Based Identification of Critical Scenarios for Cooperative and Automated Vehicles"
.
SAE International Journal of Connected and Automated Vehicles
.
1
(2). SAE International: 93.
doi
:
10.4271/2018-01-1066
.
- ^Madrigal, Story by Alexis C."Inside Waymo's Secret World for Training Self-Driving Cars".The Atlantic. RetrievedAugust 14,2020.
^
Madrigal, Story by Alexis C.
"Inside Waymo's Secret World for Training Self-Driving Cars"
.
The Atlantic
. Retrieved
August 14,
2020
.
- ^Connors, J.; Graham, S.; Mailloux, L. (2018). "Cyber Synthetic Modeling for Vehicle-to-Vehicle Applications".In International Conference on Cyber Warfare and Security. Academic Conferences International Limited: 594-XI.
^
Connors, J.; Graham, S.; Mailloux, L. (2018). "Cyber Synthetic Modeling for Vehicle-to-Vehicle Applications".
In International Conference on Cyber Warfare and Security
. Academic Conferences International Limited: 594-XI.

## Further reading

Further reading
[
edit
]
- Wooldridge, Michael (2002).An Introduction to MultiAgent Systems.John Wiley & Sons. p. 366.ISBN978-0-471-49691-5.
Wooldridge, Michael (2002).
An Introduction to MultiAgent Systems
.
John Wiley & Sons
. p. 366.
ISBN
978-0-471-49691-5
.
- Shoham, Yoav; Leyton-Brown, Kevin (2008).Multiagent Systems: Algorithmic, Game-Theoretic, and Logical Foundations.Cambridge University Press. p. 496.ISBN978-0-521-89943-7.
Shoham, Yoav; Leyton-Brown, Kevin (2008).
Multiagent Systems: Algorithmic, Game-Theoretic, and Logical Foundations
.
Cambridge University Press
. p. 496.
ISBN
978-0-521-89943-7
.
- Mamadou, Tadiou Koné; Shimazu, A.; Nakajima, T. (August 2000)."The State of the Art in Agent Communication Languages (ACL)".Knowledge and Information Systems.2(2):1–26.
Mamadou, Tadiou Koné; Shimazu, A.; Nakajima, T. (August 2000).
"The State of the Art in Agent Communication Languages (ACL)"
.
Knowledge and Information Systems
.
2
(2):
1–
26.
- Hewitt, Carl; Inman, Jeff (November–December 1991)."DAI Betwixt and Between: From "Intelligent Agents" to Open Systems Science"(PDF).IEEE Transactions on Systems, Man, and Cybernetics.21(6):1409–1419.doi:10.1109/21.135685.S2CID39080989. Archived fromthe original(PDF)on August 31, 2017.
Hewitt, Carl; Inman, Jeff (November–December 1991).
"DAI Betwixt and Between: From "Intelligent Agents" to Open Systems Science"
(PDF)
.
IEEE Transactions on Systems, Man, and Cybernetics
.
21
(6):
1409–
1419.
doi
:
10.1109/21.135685
.
S2CID
39080989
. Archived from
the original
(PDF)
on August 31, 2017.
- The Journal of Autonomous Agents and Multi-Agent Systems (JAAMAS)
The Journal of Autonomous Agents and Multi-Agent Systems (JAAMAS)
- Weiss, Gerhard, ed. (1999).Multiagent Systems, A Modern Approach to Distributed Artificial Intelligence. MIT Press.ISBN978-0-262-23203-6.
Weiss, Gerhard, ed. (1999).
Multiagent Systems, A Modern Approach to Distributed Artificial Intelligence
. MIT Press.
ISBN
978-0-262-23203-6
.
- Ferber, Jacques (1999).Multi-Agent Systems: An Introduction to Artificial Intelligence. Addison-Wesley.ISBN978-0-201-36048-6.
Ferber, Jacques (1999).
Multi-Agent Systems: An Introduction to Artificial Intelligence
. Addison-Wesley.
ISBN
978-0-201-36048-6
.
- Weyns, Danny (2010).Architecture-Based Design of Multi-Agent Systems. Springer.ISBN978-3-642-01063-7.
Weyns, Danny (2010).
Architecture-Based Design of Multi-Agent Systems
. Springer.
ISBN
978-3-642-01063-7
.
- Sun, Ron(2006).Cognition and Multi-Agent Interaction.Cambridge University Press.ISBN978-0-521-83964-8.
Sun, Ron
(2006).
Cognition and Multi-Agent Interaction
.
Cambridge University Press
.
ISBN
978-0-521-83964-8
.
- Keil, David; Goldin, Dina (2006). Weyns, Danny; Parunak, Van; Michel, Fabien (eds.).Indirect Interaction in Environments for Multiagent Systems. LNCS 3830. Vol. 3830.Springer. pp.68–87.doi:10.1007/11678809_5.ISBN978-3-540-32614-4.{{cite book}}:|journal=ignored (help)
Keil, David; Goldin, Dina (2006). Weyns, Danny; Parunak, Van; Michel, Fabien (eds.).
Indirect Interaction in Environments for Multiagent Systems
. LNCS 3830. Vol. 3830.
Springer
. pp.
68–87
.
doi
:
10.1007/11678809_5
.
ISBN
978-3-540-32614-4
.

```
{{cite book}}
```

{{
cite book
}}
:

```
|journal=
```

|journal=
ignored (
help
)
- Whitestein Series in Software Agent Technologies and Autonomic Computing, published by Springer Science+Business Media Group
Whitestein Series in Software Agent Technologies and Autonomic Computing
, published by Springer Science+Business Media Group
- Salamon, Tomas (2011).Design of Agent-Based Models : Developing Computer Simulations for a Better Understanding of Social Processes. Bruckner Publishing.ISBN978-80-904661-1-1.
Salamon, Tomas (2011).
Design of Agent-Based Models : Developing Computer Simulations for a Better Understanding of Social Processes
. Bruckner Publishing.
ISBN
978-80-904661-1-1
.
- Russell, Stuart J.;Norvig, Peter(2003),Artificial Intelligence: A Modern Approach(2nd ed.), Upper Saddle River, New Jersey: Prentice Hall,ISBN0-13-790395-2
Russell, Stuart J.
;
Norvig, Peter
(2003),
Artificial Intelligence: A Modern Approach
(2nd ed.), Upper Saddle River, New Jersey: Prentice Hall,
ISBN
0-13-790395-2
- Fasli, Maria (2007).Agent-technology for E-commerce.John Wiley & Sons. p. 480.ISBN978-0-470-03030-1.
Fasli, Maria (2007).
Agent-technology for E-commerce
.
John Wiley & Sons
. p. 480.
ISBN
978-0-470-03030-1
.
- Cao, Longbing, Gorodetsky, Vladimir, Mitkas, Pericles A. (2009).Agent Mining: The Synergy of Agents and Data Mining, IEEE Intelligent Systems, vol. 24, no. 3, 64-72.
Cao, Longbing, Gorodetsky, Vladimir, Mitkas, Pericles A. (2009).
Agent Mining: The Synergy of Agents and Data Mining
, IEEE Intelligent Systems, vol. 24, no. 3, 64-72.

<!-- table omitted -->

- v
v
- t
t
- e
e
Systems science
System
types
- Art
Art
- Biological
Biological
- Complex
Complex
- Coupled human–environment
Coupled human–environment
- Ecological
Ecological
- Economic
Economic
- Information
Information
- Multi-agent
Multi-agent
- Nervous
Nervous
- Recommender
Recommender
- Social
Social
Concepts
- Doubling time
Doubling time
- Leverage points
Leverage points
- Limiting factor
Limiting factor
- Negative feedback
Negative feedback
- Positive feedback
Positive feedback
Theoretical
fields

<!-- table omitted -->

- Control theory
Control theory
- Cybernetics
Cybernetics
- Earth system science
Earth system science
- Living systems
Living systems
- Sociotechnical system
Sociotechnical system
- Systemics
Systemics
- Urban metabolism
Urban metabolism
- World-systems theory
World-systems theory
- Analysis
Analysis
- Biology
Biology
- Dynamics
Dynamics
- Ecology
Ecology
- Engineering
Engineering
- Neuroscience
Neuroscience
- Pharmacology
Pharmacology
- Philosophy
Philosophy
- Psychology
Psychology
- Theory(Systems thinking)
Theory
(
Systems thinking
)
Scientists
- Russell L. Ackoff
Russell L. Ackoff
- Victor Aladjev
Victor Aladjev
- William Ross Ashby
William Ross Ashby
- Ruzena Bajcsy
Ruzena Bajcsy
- Béla H. Bánáthy
Béla H. Bánáthy
- Gregory Bateson
Gregory Bateson
- Stafford Beer
Stafford Beer
- Richard E. Bellman
Richard E. Bellman
- Ludwig von Bertalanffy
Ludwig von Bertalanffy
- Margaret Boden
Margaret Boden
- Alexander Bogdanov
Alexander Bogdanov
- Kenneth E. Boulding
Kenneth E. Boulding
- Murray Bowen
Murray Bowen
- Kathleen Carley
Kathleen Carley
- Mary Cartwright
Mary Cartwright
- C. West Churchman
C. West Churchman
- Manfred Clynes
Manfred Clynes
- George Dantzig
George Dantzig
- Edsger W. Dijkstra
Edsger W. Dijkstra
- Fred Emery
Fred Emery
- Heinz von Foerster
Heinz von Foerster
- Stephanie Forrest
Stephanie Forrest
- Jay Wright Forrester
Jay Wright Forrester
- Barbara Grosz
Barbara Grosz
- Charles A. S. Hall
Charles A. S. Hall
- Mike Jackson
Mike Jackson
- Lydia Kavraki
Lydia Kavraki
- James J. Kay
James J. Kay
- Faina M. Kirillova
Faina M. Kirillova
- George Klir
George Klir
- Allenna Leonard
Allenna Leonard
- Edward Norton Lorenz
Edward Norton Lorenz
- Niklas Luhmann
Niklas Luhmann
- Humberto Maturana
Humberto Maturana
- Margaret Mead
Margaret Mead
- Donella Meadows
Donella Meadows
- Mihajlo D. Mesarovic
Mihajlo D. Mesarovic
- James Grier Miller
James Grier Miller
- Radhika Nagpal
Radhika Nagpal
- Howard T. Odum
Howard T. Odum
- Talcott Parsons
Talcott Parsons
- Ilya Prigogine
Ilya Prigogine
- Qian Xuesen
Qian Xuesen
- Anatol Rapoport
Anatol Rapoport
- John Seddon
John Seddon
- Peter Senge
Peter Senge
- Claude Shannon
Claude Shannon
- Katia Sycara
Katia Sycara
- Eric Trist
Eric Trist
- Francisco Varela
Francisco Varela
- Manuela M. Veloso
Manuela M. Veloso
- Kevin Warwick
Kevin Warwick
- Norbert Wiener
Norbert Wiener
- Jennifer Wilby
Jennifer Wilby
- Anthony Wilden
Anthony Wilden
Applications
- Systems theory in anthropology
Systems theory in anthropology
- Systems theory in archaeology
Systems theory in archaeology
- Systems theory in political science
Systems theory in political science
Organizations
- List
List
- Principia Cybernetica
Principia Cybernetica
- Category
Category
- Portal
Portal
- Commons
Commons

<!-- table omitted -->

- v
v
- t
t
- e
e
Information processing
Information processes

<!-- table omitted -->

information processes by function
- perception
perception
- attention
attention
- influence
influence
- operating
operating
- communication
communication
- reasoning
reasoning
- learning
learning
- storing
storing
- decision-making
decision-making
information processing abstractions
- event processing
event processing
- sign processesing
sign processesing
- signal processing
signal processing
- data processing
data processing
- stream processing
stream processing
- agent processing
agent processing
- state processing
state processing
Information processors

<!-- table omitted -->

natural
- nature as information processing
nature as information processing
- humans as information processing systems
humans as information processing systems
- society as information processing system
society as information processing system
mixed
- mixed reality
mixed reality
- brain–computer interface
brain–computer interface
- physical computing
physical computing
- human–computer interaction
human–computer interaction
artificial
- processorsandprocesses
processors
and
processes
- bio-inspired computing
bio-inspired computing
- ubiquitous computing
ubiquitous computing
- artificial brainandmind uploading
artificial brain
and
mind uploading
- virtual reality
virtual reality
- virtual world
virtual world
Information processing
theories and concepts

<!-- table omitted -->

in biology
- computationalandsystems biology
computational
and
systems biology
- genetic informaticsandcellular computing
genetic informatics
and
cellular computing
- computational neuroscienceandneurocomputing
computational neuroscience
and
neurocomputing
in cognitive psychology
- information processing theory
information processing theory
- mindandintelligence
mind
and
intelligence
- cognitive informaticsandneuroinformatics
cognitive informatics
and
neuroinformatics
- behavior informatics
behavior informatics
in computer science
- neural computation
neural computation
- computation theory
computation theory
- algorithmsandinformation structures
algorithms
and
information structures
- computational circuits
computational circuits
- artificial intelligence
artificial intelligence
in philosophy
- computational theory of mind
computational theory of mind
- philosophy of information
philosophy of information
- philosophy of artificial intelligence
philosophy of artificial intelligence
interdisciplinary
- information theory
information theory
- decision theory
decision theory
- systems theory
systems theory
other
- infosphere
infosphere
- inforg
inforg
- Decoding the Universe
Decoding the Universe
- information overload
information overload

<!-- table omitted -->

Authority control databases
International
- GND
GND
- FAST
FAST
National
- United States
United States
- Czech Republic
Czech Republic
Other
- Yale LUX
Yale LUX
NewPP limit report
Parsed by mw‐api‐ext.codfw.main‐6569894967‐74tt2
Cached time: 20260622094502
Cache expiry: 2592000
Cache expiry source: Module:Citation/CS1 (os.date(%Y))
Reduced expiry: false
Complications: [vary‐revision‐sha1, prevent‐selective‐update, show‐toc]
CPU time usage: 0.543 seconds
Real time usage: 0.637 seconds
Preprocessor visited node count: 3455/1000000
Revision size: 32313/2097152 bytes
Post‐expand include size: 182697/2097152 bytes
Template argument size: 3837/2097152 bytes
Highest expansion depth: 12/100
Expensive parser function count: 3/500
Unstrip recursion depth: 1/20
Unstrip post‐expand size: 226542/5000000 bytes
Lua time usage: 0.354/10.000 seconds
Lua memory usage: 6687976/52428800 bytes
Number of Wikibase entities loaded: 1/500
Transclusion expansion time report (%,ms,calls,template)
100.00%  533.169      1 -total
 49.71%  265.032      1 Template:Reflist
 27.34%  145.768     20 Template:Cite_journal
 12.29%   65.532     15 Template:Cite_book
  8.25%   43.968      1 Template:Multi-agent_system
  8.07%   43.003      1 Template:Short_description
  7.69%   41.014      1 Template:Sidebar_with_collapsible_lists
  7.60%   40.530     10 Template:Cite_web
  6.29%   33.556      1 Template:Authority_control
  6.24%   33.275      6 Template:Navbox
Render ID 0a3cf4e4-6e1f-11f1-854f-01e42f2cb470
Saved in parser cache with key enwiki:pcache:938833:|#|:idhash:canonical and timestamp 20260622094502 and revision id 1360572309. Rendering was triggered because: unknown
Retrieved from "
https://en.wikipedia.org/w/index.php?title=Multi-agent_system&oldid=1360572309
"
Categories
:
- Multi-agent systems
Multi-agent systems
- Management theory
Management theory
Hidden categories:
- CS1 maint: year
CS1 maint: year
- CS1 maint: location missing publisher
CS1 maint: location missing publisher
- Articles with short description
Articles with short description
- Short description is different from Wikidata
Short description is different from Wikidata
- Use mdy dates from October 2023
Use mdy dates from October 2023
- All articles with unsourced statements
All articles with unsourced statements
- Articles with unsourced statements from December 2016
Articles with unsourced statements from December 2016
- Pages using div col with small parameter
Pages using div col with small parameter
- CS1 errors: periodical ignored
CS1 errors: periodical ignored