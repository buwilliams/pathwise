# Building Independence — A Life-Strategy Model for Teens

The implementation of this model is the [pathwise](https://github.com/buwilliams/pathwise) app. This document defines the model. It does not draw a conclusion about what any specific teen should do.

## 1. Problem Domain: Considerations and Symbol Definitions

A teen graduating high school is beginning the transition into adult life. They want more independence and are considering major life decisions such as buying a car, working more, moving out, and choosing a path toward higher income.

These decisions are emotionally heavy because they are not isolated. A car affects money, mobility, job options, insurance, maintenance, and savings. Moving out affects independence, rent burden, work hours, stress, future options, and available time. Skill-building affects future income, but requires time, money, discipline, and delayed gratification.

The purpose of this model is not to prove the one correct answer. The purpose is to make the important factors explicit so we can use conjecture and criticism to evaluate possible paths.

The guiding idea is:

> A good plan should generate positive momentum across their values, time, and assets, without creating excessive fragility.

### Core Life-State Model

Let:

$$
L = \{V, T, A, Y, K, H\}
$$

Where:

| Symbol | Meaning |
|---|---|
| $L$ | Life-state |
| $V$ | Values |
| $T$ | Time |
| $A$ | Assets |
| $Y$ | Income |
| $K$ | Skills / credentials |
| $H$ | Emotional cost |

A life-state is not just whether a teen can afford something today. A life-state describes whether their overall situation is becoming stronger, weaker, freer, or more fragile.

Two further symbols, fragility ($F$) and recoverability ($R$), are introduced later but sit outside $L$ on purpose. $F$ is a derived measure of how exposed a life-state is to shocks. $R$ is a property of a particular decision, not of the state itself.

### Values

Let:

$$
V = \{i, n, e, g, s\}
$$

Where:

| Symbol | Meaning |
|---|---|
| $i$ | Independence |
| $n$ | Positive net worth |
| $e$ | Enjoyable life experience |
| $g$ | Goal progress |
| $s$ | Stability / emotional safety |

Independence should not be treated as one simple thing. A teen may want independence, but different forms of independence can conflict with one another.

Let:

$$
I = \{i_1, i_2, i_3, i_4\}
$$

Where:

| Symbol | Type of Independence | Meaning |
|---|---|---|
| $i_1$ | Mobility independence | Reliable transportation; ability to get to work, school, friends, appointments, and opportunities |
| $i_2$ | Financial independence | Positive cash flow, preserved savings, and reduced dependence on others for money |
| $i_3$ | Residential independence | Living outside a parent's home |
| $i_4$ | Decision independence | More control over schedule, choices, goals, and personal life |

A key conjecture:

> Moving out increases residential independence, but may reduce financial independence if rent consumes too much income.

In notation:

$$
i_3 \uparrow \Rightarrow i_2 \downarrow
$$

This means moving out may feel like independence while reducing total practical freedom.

### Emotional Cost

Let:

$$
H = \text{emotional cost}
$$

Many decisions carry an emotional cost beyond their financial one. Staying with a parent saves money but can pay in privacy, autonomy, conflict, infantilization, or feeling stuck. A draining job or long commute pays in chronic stress and lost time. An intensive training path pays in discipline cost, delayed gratification, and self-doubt. The wrong roommate pays in friction. Even a car can pay in maintenance anxiety, traffic fatigue, or the pressure of an insurance bill. These costs are real even when they do not appear on a balance sheet.

The model should not treat any choice as emotionally free by default. $H$ varies by scenario. $H(s)$ is paid in reductions to $e$ (enjoyable life) and $s$ (stability / emotional safety), and sometimes in $g$ (goal progress) when emotional pressure blocks momentum.

Examples:

| Choice | Possible emotional cost |
|---|---|
| Stay at home | Privacy, autonomy, conflict, family stress |
| Move out | Financial pressure, isolation, household labor, instability of a new arrangement |
| Long-hour job | Chronic stress, fatigue, lost social and rest time |
| Intensive training | Discipline cost, delayed gratification, self-doubt |
| Car ownership | Maintenance anxiety, commute fatigue, repair stress |

This matters because comparing two choices requires comparing their full costs, not just their financial ones. A choice that looks cheaper financially can be more expensive emotionally, and a choice that looks expensive financially can pay for itself in restored peace, energy, or pride.

In notation:

$$
\text{a choice becomes more attractive as } H(\text{alternative}) - H(\text{this choice}) \text{ rises}
$$

Plain English:

> A plan that saves money but destroys peace is not a good plan. A plan that costs money but restores peace can be the right plan when the emotional gain is real.

### Time

Let:

$$
T = \{p, b, q\}
$$

Where:

| Symbol | Meaning |
|---|---|
| $p$ | Productive hours available per week |
| $b$ | Buffer hours for unexpected events, rest, family, errands, and chaos |
| $q$ | Quality of time / energy level |

Time is not only the number of hours available. Two plans may leave the same number of free hours, but one may leave a teen exhausted while the other leaves them with enough energy to build their future.

A useful distinction:

$$
p_{theoretical} \neq p_{actual}
$$

A plan can work on paper but fail if the remaining hours are low-quality, tired, scattered, or emotionally overloaded.

### Assets

Let:

$$
A = \{c, \sigma, d, r\}
$$

Where:

| Symbol | Meaning |
|---|---|
| $c$ | Monthly cash flow |
| $\sigma$ | Savings |
| $d$ | Debt / liabilities |
| $r$ | Risk buffer / emergency fund |

A teen who has built up meaningful savings has options. The goal is not merely to spend savings on adult things, but to preserve enough savings that they remain resilient.

A plan becomes fragile when:

$$
c < 0
$$

or:

$$
r < r_{min}
$$

A plan may be technically possible but still undesirable if it destroys cash flow or risk buffer.

### Income

Let:

$$
Y = \{y, y_{min}, y_{growth}\}
$$

Where:

| Symbol | Meaning |
|---|---|
| $y$ | Current income |
| $y_{min}$ | Minimum income threshold for desirable independence |
| $y_{growth}$ | Likely income growth over time |

The income question is not only:

> How much do they make today?

It is also:

> What income level would make their desired life-state actually sustainable?

A useful conjecture:

> Residential independence becomes desirable only when income is high enough that housing, transportation, savings, and enjoyable life can all coexist without excessive pressure.

### Skills and Credentialing

Let:

$$
K = \{k, \tau, \mu, \rho\}
$$

Where:

| Symbol | Meaning |
|---|---|
| $k$ | A specific skill or credential path |
| $\tau$ | Time required to acquire it |
| $\mu$ | Money required to acquire it |
| $\rho$ | Risk / uncertainty of completion or payoff |

Skills and credentials matter because they can transform the income variable.

$$
K \rightarrow Y
$$

Or more fully:

$$
K \rightarrow Y \rightarrow A \rightarrow T \rightarrow V
$$

This means skill-building is not merely another goal. It is a lever that changes what life-states are possible.

### Desirable Life-State

Define:

$$
L_{desirable} = \{L_s : V_s \geq V_{min} \land T_s \geq T_{min} \land A_s \geq A_{min} \land Y_s \geq Y_{min}\}
$$

Plain English:

> A desirable life-state is one where values, time, assets, and income all meet minimum acceptable thresholds.

A key distinction:

$$
L_{possible} \neq L_{desirable}
$$

A life-state can be possible without being desirable.

Example:

A teen may be able to move out if they work enough hours, but if the plan leaves them broke, tired, stressed, unable to save, and unable to build future skills, then it may be possible but not desirable.

### Positive Momentum

The target is not merely independence today. The target is positive momentum.

Let:

$$
Momentum(L) = f(V, T, A, Y, K, H)
$$

A plan has positive momentum when their values, time, assets, income, and skill path reinforce one another while emotional cost stays low.

A good plan should tend toward:

$$
i \uparrow, \quad n \uparrow, \quad e \uparrow, \quad g \uparrow, \quad s \uparrow
$$

while preserving:

$$
c \geq 0, \quad r \geq r_{min}, \quad p \geq p_{min}
$$

Plain English:

> A good plan should increase independence, net worth, enjoyment, goal progress, and stability while maintaining positive cash flow, enough emergency buffer, and enough productive time.

### Fragility

Let:

$$
F = \text{fragility}
$$

Fragility increases when there is too little money, too little time, too much debt, too much pressure, or too little room for mistakes.

A plan should satisfy:

$$
F(L_j) \leq F_{max}
$$

for each stage of the plan.

Plain English:

> No step should make life so fragile that a small mistake, emergency, repair, illness, or job disruption causes the whole plan to fail.

### Recoverability

Let:

$$
R = \text{recoverability}
$$

Recoverability measures how easily a teen can reverse, repair, or step back from a decision if it turns out badly. Trying a part-time job, taking a short course, or getting insurance quotes before buying are high-recoverability decisions. Signing a year lease they can barely afford, taking on high-interest debt, or buying a car that drains their emergency fund are low-recoverability decisions.

Recoverability is distinct from fragility. Fragility describes how exposed a life-state is to shocks. Recoverability describes how easily a *specific decision* can be undone if it turns out wrong. A decision can be recoverable even when the resulting life-state is fragile (a short lease in a city they can leave) and irrecoverable even when the life-state looks safe (a long contract that locks in obligations).

A plan should satisfy:

$$
R(s_j) \geq R_{min}
$$

for each step $j$ where the decision is large enough that an error would meaningfully change the path.

Plain English:

> Prefer decisions that can be stepped back from. Irreversible decisions need more evidence than reversible ones.

---

## 2. Scenario Modeling and Path Evaluation

This section treats life choices as candidate scenarios and sequences of scenarios. The goal is to compare paths, not merely isolated decisions.

### Candidate Scenarios

Let:

$$
S = \{s_1, s_2, s_3, \dots, s_k\}
$$

Where each $s$ is a possible scenario or life strategy.

Examples:

| Scenario | Description |
|---|---|
| $s_1$ | Stay home, buy no car, save aggressively |
| $s_2$ | Stay home, buy modest car, preserve savings buffer |
| $s_3$ | Move out, buy car |
| $s_4$ | Move out, no car |
| $s_5$ | Stay low-rent, buy reliable modest car, pursue income/credential path, move out later |
| $s_6$ | Work more hours immediately, save more money, delay car purchase |
| $s_7$ | Keep current work, add training or school, delay apartment independence |

Each scenario produces an outcome:

$$
O(s) = L_s
$$

Where:

$$
L_s = \{V_s, T_s, A_s, Y_s, K_s, H_s\}
$$

Plain English:

> Each possible plan creates a different life-state.

### Viability Filter

Before ranking scenarios by preference, first remove scenarios that are too fragile.

Define:

$$
S_{viable} = \{s \in S : c_s \geq 0 \land r_s \geq r_{min} \land p_s \geq p_{min}\}
$$

Plain English:

> The viable scenarios are all scenarios in $S$ where cash flow is nonnegative, risk buffer is high enough, and productive time is high enough.

This prevents us from being fooled by a plan that feels exciting but creates a brittle life.

A scenario is not viable if any of these fail:

$$
c_s < 0
$$

$$
r_s < r_{min}
$$

$$
p_s < p_{min}
$$

### Desirability Filter

A viable scenario is not automatically desirable. It may be survivable but not good.

Define:

$$
S_{desirable} = \{s \in S_{viable} : L_s \in L_{desirable}\}
$$

Plain English:

> Desirable scenarios are viable scenarios that also create a life-state worth wanting.

This distinction matters:

$$
S_{desirable} \subseteq S_{viable} \subseteq S
$$

Meaning:

> Desirable scenarios are a subset of viable scenarios, and viable scenarios are a subset of all possible scenarios.

### Momentum Score

Once nonviable plans are removed, we can compare the remaining plans by momentum.

Let:

$$
Momentum(s) = w_i i_s + w_n n_s + w_e e_s + w_g g_s + w_s s_s + w_p p_s + w_c c_s + w_r r_s + w_y y_s
$$

Where the $w$'s are weights representing importance.

Possible initial weights:

| Variable | Meaning | Suggested Weight |
|---|---|---:|
| $i$ | Independence | 2 |
| $n$ | Positive net worth | 3 |
| $e$ | Enjoyable life | 2 |
| $g$ | Goal progress | 3 |
| $s$ | Stability / emotional safety | 4 |
| $p$ | Productive time | 2 |
| $c$ | Cash flow | 4 |
| $r$ | Risk buffer | 4 |
| $y$ | Income | 3 |

Cash flow, risk buffer, and emotional stability should likely receive high weights because when they collapse, the whole life-state becomes fragile.

Emotional cost $H$ does not appear directly in the score. Its effect flows through $e_s$, $s_s$, and $g_s$, which it depresses when high. The weights on those three carry the emotional load.

The best scenario is:

$$
s^* = \arg\max_{s \in S_{viable}} Momentum(s)
$$

Plain English:

> The best scenario is the viable scenario with the highest positive momentum.

### Path-Based Evaluation

A teen's life should not be modeled as one giant decision. It should be modeled as a path.

Let:

$$
P = (s_0, s_1, s_2, \dots, s_n)
$$

Where $P$ is a sequence of scenarios or stages.

Example path:

$$
P_1 = \text{stay low-rent} \rightarrow \text{buy modest car} \rightarrow \text{increase income} \rightarrow \text{move out later}
$$

The goal is:

$$
L_0 \rightarrow L_1 \rightarrow L_2 \rightarrow \dots \rightarrow L^*
$$

Where:

$$
L^* \in L_{desirable}
$$

Plain English:

> The best plan is the sequence of moves that gets a teen from their current life-state to a desirable life-state without creating too much fragility along the way.

### Path Objective

Let:

$$
\mathcal{P} = \{P_1, P_2, P_3, \dots, P_m\}
$$

Where $\mathcal{P}$ is the set of possible paths.

Then:

$$
P^* = \arg\max_{P \in \mathcal{P}} Momentum(P)
$$

Subject to:

$$
L_n \in L_{desirable}
$$

and:

$$
F(L_j) \leq F_{max} \quad \text{for each step } j
$$

and:

$$
R(s_j) \geq R_{min} \quad \text{for each large decision } j
$$

Plain English:

> The best path is the path with the most positive momentum, ending in a desirable life-state, while keeping fragility below the danger threshold at each step and ensuring that large decisions remain recoverable.

### Independence Ladder

Instead of treating independence as binary, model it as a ladder.

$$
i_1 \rightarrow i_2 \rightarrow i_3 \rightarrow i_4
$$

Where:

| Stage | Independence Type | Practical Meaning |
|---|---|---|
| $i_1$ | Mobility independence | Reliable transportation |
| $i_2$ | Financial independence | Positive cash flow and savings |
| $i_3$ | Residential independence | Living outside a parent's home |
| $i_4$ | Decision independence | Control over life choices and direction |

The ladder is a structural claim about the model: independence is multi-dimensional, and gains in one dimension can come at the cost of another. The model does not prescribe an ordering. Different paths may climb the ladder in different orders, and the momentum, viability, and recoverability filters are what distinguish good orderings from bad ones in any given case.

### Model-Level Falsifiability

The model itself is a conjecture and should be revisable. Conditions that should trigger revision:

- A scenario produces high momentum but feels emotionally wrong to the teen. (A value is missing or mis-weighted.)
- A scenario looks viable on paper but fails repeatedly in practice. (A constraint is uncosted.)
- The teen's stated values shift in a stable, considered way. ($V$ needs updating.)
- A variable in $L$ turns out to be redundant, or a needed variable is missing.
- The weights in $Momentum(s)$ produce rankings that contradict considered judgment across many scenarios.

Plain English:

> The model is a tool for thinking, not a verdict. When it stops fitting reality, change the model.

---

## 3. Questions to Sort Through

This section is for discovering values, desires, constraints, and hidden tradeoffs. The goal is not to interrogate. The goal is to help a teen sort through what they want and what each possible path would actually cost or create.

### Questions: Independence

1. When you say you want independence, what does that mean to you right now?
2. Which feels most important: having your own car, having your own place, making your own decisions, or not needing help with money?
3. What parts of your current situation make you feel least independent?
4. What would make you feel more like an adult?
5. What kind of independence are you willing to wait for if waiting makes it more stable?
6. What kind of independence feels urgent?
7. Do you want independence from something, independence toward something, or both?

### Questions: Car

1. What would having a car unlock for you?
2. Is the car mainly about work, friends, freedom, privacy, school, dating, or not relying on others?
3. How often would you realistically use the car each week?
4. What would life look like without a car for the next 6–12 months?
5. What is the maximum amount of your savings you would feel comfortable spending on a car?
6. How much emergency money do you want left after buying a car?
7. Would you rather have a nicer car and less savings, or a modest car and more safety?
8. How would you feel if the car needed a $1,000 repair three months after buying it?

### Questions: Money

1. How much money do you want to keep untouched as an emergency fund?
2. How much monthly pressure feels okay, and how much feels scary?
3. What bills do you expect to pay yourself?
4. What bills do you hope someone else helps with for now?
5. How important is it to keep saving money every month?
6. How would you feel if your savings dropped from $10,000 to $3,000?
7. How would you feel if your savings dropped near zero but you had a car?
8. What does "financially safe" feel like to you?

### Questions: Work and Income

1. How do you feel about your current job?
2. Do you want to work more hours, fewer hours, or about the same?
3. What parts of work give you energy?
4. What parts of work drain you?
5. How much income would make you feel more secure?
6. Would you rather work more now, train for better income, or do some of both?
7. What kind of work do you not want to be doing two years from now?
8. What kind of work could you imagine feeling proud of?

### Questions: Skills and Credentials

1. Are there any jobs, careers, or lifestyles that seem interesting to you?
2. Would you rather learn through school, hands-on work, online training, apprenticeship, or a short certificate?
3. How long are you willing to train for a better income path?
4. What subjects or activities come naturally to you?
5. What do people often tell you you are good at?
6. What kind of work environment would you hate?
7. What kind of work environment would fit your personality?
8. Would you rather optimize for money, flexibility, meaningful work, stability, or low stress?

### Questions: Moving Out

1. What feels hard about staying where you are?
2. What do you imagine would feel better if you moved out?
3. What would you be afraid of if you moved out?
4. What would make moving out feel safe rather than stressful?
5. Would you rather move out sooner with more financial pressure or later with more stability?
6. What would be a good reason to delay moving out?
7. What would be a good reason to move out sooner?
8. If moving out meant working so much that you had less time for friends, goals, or rest, would it still feel worth it?

### Questions: Enjoyable Life

1. What does a good week look like to you?
2. How much time do you want for friends?
3. How much time do you want for rest and doing nothing?
4. What activities make life feel worth living?
5. What would make adult life feel exciting rather than heavy?
6. What are you afraid of losing as you take on more responsibility?
7. What do you want to protect in your life even while growing up?

### Questions: Future Self

1. What would make you proud one year from now?
2. What would make you feel stuck one year from now?
3. What do you hope your life looks like next year?
4. What do you hope your money situation looks like next year?
5. What do you hope your work situation looks like next year?
6. What do you hope your relationships and social life look like next year?
7. What is one thing you would like future-you to thank current-you for?

### Questions for the Helper

For a parent, mentor, coach, or anyone helping a teen sort through this:

1. Am I helping them clarify their desires, or am I subtly replacing them with mine?
2. Am I protecting them from a bad decision, or protecting myself from the discomfort of watching them struggle?
3. Have I separated my values from theirs?
4. Am I giving them enough agency in the process?
5. Am I making the complexity simpler for them, or accidentally making them feel more overwhelmed?
6. Am I presenting conclusions too early before they feel heard?
7. Am I treating their desire for independence as legitimate, even when I think their current strategy may be flawed?
8. Am I helping them become capable, or merely helping them avoid mistakes?

### Questions for the Helper: Model Quality

1. What important variables are missing from the model?
2. Which assumptions are guesses that need better information?
3. Which costs are recurring, and which are one-time?
4. Which risks are likely, and which are catastrophic but rare?
5. Which scenario creates the most positive momentum?
6. Which scenario feels good emotionally but fails structurally?
7. Which scenario is financially safe but emotionally unacceptable?
8. Which path gives them the most real independence over 12–24 months?
9. What would make moving out sooner a good plan?
10. What would make buying a car now a good plan?
11. What would make delaying both the car and apartment a good plan?

### Questions for the Helper: Communication

1. What is the next small conversation, not the whole mountain?
2. What does the teen need to feel before they can hear the math?
3. What part of the plan should be shared now, and what part should remain in my working model?
4. How can I communicate that I am on their side?
5. How can I make the model feel empowering rather than controlling?
6. How can I show respect for what they have already built (savings, hours worked, things they have figured out)?
7. How can I help them feel proud before discussing tradeoffs?
8. How can I present criticism of bad plans without making them feel criticized?

### Core Conversation Frame

A possible way to frame the whole process:

> "I know you want more independence, and I respect that. I do not want to take over your choices. I want to help you sort through the tradeoffs so your choices actually create more freedom, not more pressure. You bring the desires. I'll help with the math, the options, and the plan."

Another possible frame:

> "You do not have to become independent all at once. We can figure out the order that gives you the most real freedom with the least unnecessary stress."
