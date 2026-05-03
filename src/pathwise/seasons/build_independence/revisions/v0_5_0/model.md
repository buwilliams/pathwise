# Building Independence — A Life-Strategy Model

The implementation of this model is the [pathwise](https://github.com/buwilliams/pathwise) app. This document defines the model. It does not draw a conclusion about what any specific teen should do.

You are graduating high school, turning 18, and beginning the transition into adult life. You want more independence and are considering major life decisions: a car, more work, moving out, a path toward higher income, what to do about friendships and relationships. These decisions are not isolated. A car affects money, mobility, job options, insurance, and savings. Moving out affects independence, rent burden, work hours, stress, and time. Pursuing education affects future income but costs time, money, discipline, and delayed gratification.

The purpose of this model is not to prove the one correct answer. The purpose is to make the important factors explicit so you (or whoever is helping you) can use conjecture and criticism to evaluate possible paths.

The document has three main sections. Section 1 states the core conjecture. Section 2 formalizes it. Section 3 walks through the formalization in detail.

---

## 1. Conjecture

Time is your most valuable resource. It is finite and spent whether or not you choose where it goes. A good life is one where time is directed at enjoyment.

Enjoyment is not the absence of difficulty. Hardship pursued toward an outcome you want is a good use of time. Hardship endured for an outcome you don't want is poor use of time. The goal modifies the difficulty from a good to a bad use of time.

The lived experience along the way is most of life. A path that ends well but spends years in misery is not the same as a path that ends equally well and is good to live through. The journey is what you live. Destinations are milestones along the journey.

The conjecture is that the best path is one that creates **momentum**: each step moves your life-state toward something more desirable, not merely something survivable.

That momentum must be adjustable, enjoyable to live through, and digestible.

- **Adjustable**: the path is not chosen once. It is revised at each stage as new information arrives. An adjustable path requires that each step remain reversible enough to actually redirect. An irreversible decision shrinks future options regardless of whether it was good at the time.
- **Enjoyable**: the path is judged by the lived experience across stages, not only by where it ends.
- **Digestible**: the helper's role is to wrap the complexity of scarcity tradeoffs and path dependency in a presentation digestible for a teenager. The formalization below is the mental work of a mature adult doing the heavy lifting.

---

## 2. Formalized Model

### 2.1 State

$$
L = \{V, T, A, K, W\}
$$

$$
V = \{i_1, i_2, i_3, i_4, e, g, \beta\}
$$

$$
T = \{p, b, q\}
$$

$$
A = \{c, \sigma, d, r, y, \gamma\}
$$

$$
K = \{k, \tau, \mu, \rho, \delta\}
$$

$$
W = \{\phi, \psi, \zeta, \eta, \nu\}
$$

| Symbol | Meaning |
|---|---|
| $L$ | Life-state |
| $V$ | Values |
| $T$ | Time |
| $A$ | Assets (including income) |
| $K$ | Education |
| $W$ | Health |
| $i_1, i_2, i_3, i_4$ | Mobility, financial, residential, decision independence |
| $e$ | Enjoyable life experience |
| $g$ | Goal progress |
| $\beta$ | Stability / emotional safety |
| $p$ | Productive hours per week |
| $b$ | Buffer hours |
| $q$ | Quality of time / energy |
| $c$ | Monthly cash flow |
| $\sigma$ | Savings |
| $d$ | Debt / liabilities |
| $r$ | Risk buffer / emergency fund |
| $y$ | Income |
| $\gamma$ | Income growth rate |
| $k$ | Education path |
| $\tau$ | Time required for $k$ |
| $\mu$ | Money required for $k$ |
| $\rho$ | Completion / payoff risk for $k$ |
| $\delta$ | Technology trajectory of $k$ |
| $\phi$ | Physical health |
| $\psi$ | Mental health |
| $\zeta$ | Fitness practice (diet, exercise) |
| $\eta$ | Net emotional impact (signed) |
| $\nu$ | Relational quality |

Subscripts: $x_s$ denotes $x$ in scenario $s$; $x_j$ denotes $x$ at stage $j$ of a path. Thresholds ($r_{min}$, $\phi_{min}$, $y_{min}$, $H$, $R_{min}$, etc.) are person-specific parameters.

Because time is finite and the most valuable resource, it enters the model in three places: as the state variables in $T = \{p, b, q\}$, as stage durations $d_j$ weighting path momentum (§2.5), and as a horizon budget $H$ that bounds the total stage durations a path may spend.

### 2.2 Cross-Variable Relationships

Education's effects on time, assets, and projected income:

$$
p_{actual} = p_{baseline} - \tau_{weekly} \quad \text{during training}
$$

$$
\sigma_{after} = \sigma_{before} - \mu
$$

$$
E[\Delta y] = (1 - \rho) \cdot \Delta y_{\text{if complete}}
$$

$$
\hat{y}(L_s, H) = y_s \cdot (1 + \gamma_s)^H \cdot (1 + \delta_s)^H
$$

Emotional comparison between alternatives:

$$
\text{a choice becomes more attractive as } \eta(\text{this}) - \eta(\text{alternative}) \text{ rises}
$$

### 2.3 Viable and Desirable

$$
L_{viable} = \{L : c \geq 0 \land r \geq r_{min} \land p \geq p_{min} \land b \geq b_{min} \land q \geq q_{min} \land \phi \geq \phi_{min} \land \psi \geq \psi_{min} \land \nu \geq \nu_{min}\}
$$

$$
L_{desirable} = L_{viable} \cap \{L : i_1 \geq i_{1,min} \land i_2 \geq i_{2,min} \land i_3 \geq i_{3,min} \land i_4 \geq i_{4,min} \land e \geq e_{min} \land g \geq g_{min} \land \beta \geq \beta_{min} \land y \geq y_{min} \land \sigma \geq d \land \hat{y}(L, H) \geq y_{min} \land \zeta \geq \zeta_{min} \land \eta \geq \eta_{min}\}
$$

$$
S_{viable} = \{s \in S : L_s \in L_{viable}\}, \quad S_{desirable} = \{s \in S : L_s \in L_{desirable}\}
$$

$$
S_{desirable} \subseteq S_{viable} \subseteq S
$$

### 2.4 Adjustable

The path objective is applied iteratively. At each stage $j$, re-optimize over the paths still reachable from $L_j$:

$$
P^*_j = \arg\max_{P \in \mathcal{P}_j} Momentum(P)
$$

subject to the constraints in §2.5. Take $s_{j+1}$ as the first step of $P^*_j$. Observe $L_{j+1}$. Re-optimize. The model is a policy, not a fixed plan. As stages elapse, the remaining horizon shrinks; each re-optimization is bounded by $H - \sum_{k<j} d_k$, not the full $H$.

For the path to remain adjustable, individual decisions must stay reversible enough that future redirection is possible. Define how recoverable a decision is:

$$
R(s_j) = 1 - \frac{w_\lambda \lambda_j + w_\xi \xi_j + w_\Delta \Delta_j}{w_\lambda + w_\xi + w_\Delta}
$$

Where $\lambda_j, \xi_j, \Delta_j \in [0, 1]$ measure lock-in duration (as a fraction of $H$), exit cost (as a fraction of $\sigma$), and state disruption (fraction of $L$ materially altered). $w_\lambda, w_\xi, w_\Delta$ are person-specific weights. $R(s_j) \in [0, 1]$. The path objective requires $R(s_j) \geq R_{min}$ for each large decision.

### 2.5 Momentum and Path Objective

$$
Momentum(L) = w_{qe} \cdot q \cdot e \;+\; \sum_{x \in components(L)} w_x \cdot x
$$

Where $components(L)$ ranges over the scored scalar sub-components of $V$, $T$, $A$, and $W$: $i_1, i_2, i_3, i_4, e, g, \beta, p, b, q, c, \sigma, r, y, \gamma, \phi, \psi, \zeta, \eta, \nu$. ($K$'s sub-components and $d$ are tracked but not directly scored.) The leading $q \cdot e$ term operationalizes "time directed at enjoyment"; the additive sum of $g$ and $\eta$ operationalizes "the goal modifies the difficulty." See §3.5.

Single-scenario optimum:

$$
s^* = \arg\max_{s \in S_{desirable}} Momentum(s)
$$

Path: $P = (s_0, s_1, \dots, s_n)$. Path momentum sums life-state quality across stages, weighted by stage duration $d_j$:

$$
Momentum(P) = \sum_{j=0}^{n} d_j \cdot Momentum(L_j)
$$

Path objective:

$$
P^* = \arg\max_{P \in \mathcal{P}} Momentum(P)
$$

subject to:

$$
L_n \in L_{desirable}, \quad L_j \in L_{viable} \;\forall j, \quad R(s_j) \geq R_{min} \;\forall \text{ large decisions } j
$$

and the horizon budget:

$$
\sum_{j=0}^{n} d_j \leq H
$$

---

## 3. Explanation

This section walks through Section 2 in order. Each subsection explains the reasoning behind a piece of the formalization: why it exists, why the choices in it were made, and what it captures from the conjecture.

### 3.1 State

Why model life as a state? Because the decisions you face are not isolated. Buying a car changes mobility, money, schedule, stress, savings, and friendships all at once. A choice that improves one thing can quietly damage another. To compare candidate decisions honestly, the model needs a snapshot wide enough to be useful. No model captures everything. The goal is enough scope to surface the load-bearing tradeoffs without becoming unwieldy.

Why these five dimensions and not four or seven? Each can move without dragging the others with it. You can be financially comfortable but exhausted, or healthy but broke, or skilled but lonely. Collapsing two dimensions into one would hide a tradeoff you actually face. The five chosen here are a working compromise between coverage and simplicity. If a needed dimension turns out to be missing, §3.6 lists that as a falsifiability trigger.

A life-state $L$ has five top-level dimensions: values ($V$), time ($T$), assets ($A$), education ($K$), and health ($W$). Reasoning about life decisions requires reasoning about all of them.

#### Values ($V$)

Why values as a separate dimension? Because what you have is not the same as what you want. Two paths can leave you in identical financial and physical states with very different feelings about whether you are living the life you want. Values are the dimension that captures whether your situation matches what you actually care about.

Seven sub-components: four independence types plus enjoyable life experience ($e$), goal progress ($g$), and emotional safety ($\beta$).

Independence is decomposed into four because the sub-types can conflict. The canonical example is moving out: it raises $i_3$ (residential independence) while often reducing $i_2$ (financial independence). Mobility ($i_1$) is reliable transportation. Decision independence ($i_4$) is control over schedule, choices, and direction. The model does not prescribe an ordering for climbing them; different paths build different orders, and the momentum, viable, and recoverable filters distinguish good orderings from bad ones in any given case.

Net worth is not in $V$. It is captured by $\sigma$ and $d$ in $A$, with the desirable filter requiring $\sigma_s \geq d_s$.

#### Time ($T$)

Why split time into three? Because counting available hours is not enough. Hours that are exhausted, scattered, or all spoken for in advance behave very differently from rested hours that can actually build a life. A plan with sixty grinding hours is not the same as a plan with sixty energetic hours.

Three sub-components: count ($p$), buffer ($b$), and quality ($q$).

Time is more than the count of available hours. Two plans may leave the same number of free hours but one leaves you exhausted while the other leaves you with energy to build a life. Each of $p$, $b$, and $q$ is a viable-state floor. A plan that wins on $p$ but collapses $q$ is not viable.

A useful distinction: $p_{theoretical} \neq p_{actual}$. A plan can work on paper but fail if the remaining hours are tired, scattered, or emotionally overloaded.

Time is the most valuable resource in the model. It enters in three places: as the state variables in $T$, as stage durations $d_j$ that weight path momentum, and as a horizon budget $H$ that bounds the total time a path may spend.

#### Assets ($A$)

Why bundle income and assets together? Because they cannot be reasoned about separately. A high income with high spending leaves you fragile. A low income with low overhead leaves you resilient. Cash flow is the difference between income and outflow. Savings is what cash flow accumulates. Splitting these across separate top-level dimensions would force the model to constantly re-couple them.

Six sub-components: monthly cash flow ($c$), savings ($\sigma$), debt ($d$), risk buffer ($r$), income ($y$), and growth rate ($\gamma$).

Assets are everything financial: what comes in, what is held, what is owed, what is set aside, what flows month to month, and what is projected to change.

A plan becomes financially fragile when $c < 0$ or $r < r_{min}$. A plan that meets those floors but produces $y < y_{min}$ is viable without being desirable: it can survive without yet supporting the life you want. $y_{min}$ is a desirable-state threshold, not a survival threshold.

A useful conjecture: residential independence becomes desirable only when income is high enough that housing, transportation, savings, and enjoyable life can all coexist without excessive pressure.

#### Education ($K$)

Why education as its own dimension? Because it is the main lever you have on income, and through income on the rest of the asset base. Health, time, and values are things you already have and modify. Education is the thing you invest in now to change what is possible later.

Five sub-components: a path ($k$), training time ($\tau$), training money ($\mu$), completion risk ($\rho$), and technology trajectory ($\delta$).

Education here covers any path that builds skill or credential, formal or informal: school, certificate, apprenticeship, on-the-job learning, self-study, mentorship. The model treats them as one category because what matters is the resulting capability, not the venue.

Education is a lever on income. The chain $K \rightarrow A \rightarrow T \rightarrow V$ says it formally: $K$ lifts $y$ inside $A$, and that lift propagates to $c$, $\sigma$, and $r$. With more $A$, you can spend money to free time (a reliable car, less commute, fewer side jobs), which raises both the count and quality of $T$. With better $T$, every dimension of $V$ can move.

$\delta$ (technology trajectory) reflects that the $K \rightarrow y$ relationship is not stable across time. People create new knowledge, knowledge produces new technology, and technology reshapes which education paths the market pays for. $\delta$ is signed: negative if exposed to displacement by emerging technology, near zero if tech-neutral over the relevant horizon, positive if amplified.

$\delta$ cannot be measured with confidence. The point is not to forecast precisely but to refuse the assumption that today's job market describes tomorrow's. A useful question for any candidate path: if the most plausible technology trajectory in this field plays out over $\tau$, does this education path still produce the income it does today? When the answer is no, $\rho$ should rise and the path should favor education that remains valuable as the field changes.

$\delta$ and $\gamma$ are independent. A field can decline while a particular practitioner sees positive $\gamma$ from accumulated experience, geographic advantage, or moving up the value chain. Conversely, $\gamma$ can be negative for personal reasons (a career change, a location move, a step back into training) while $\delta$ stays neutral.

#### Health ($W$)

Why model health holistically? Because the dimensions of well-being are not interchangeable. A plan can succeed financially while the body decays. Another can sustain physical health while loneliness grows. Treating health as a single number would let one of these masquerade as the other. The five sub-components let the model see each dimension on its own.

Five sub-components: physical ($\phi$), mental ($\psi$), fitness ($\zeta$), emotional impact ($\eta$), and relational quality ($\nu$).

Health is treated holistically: the full state of body, mind, behavior, emotion, and social connection. Each dimension is real, and a plan that wins on every other axis but ruins any of them is not a good plan. Each dimension affects the others, but they are tracked separately because a plan can be strong in one and quietly destroying another. Long hours can sustain mental focus while degrading physical health and fitness. A meaningful job can lift emotional impact while crowding out relational quality.

$\phi$ and $\psi$ are the slow underlying state of body and mind. They compound over years. A long commute eats sleep. A high-pressure job raises baseline anxiety. Skipped exercise and poor diet compound silently. A path that produces strong income but ruins $\phi$ or $\psi$ is a path that pays interest forever, often at the worst time.

$\zeta$ is the practice, not the state: what you actually do day to day around movement and food. State ($\phi$) follows practice ($\zeta$) over time. A plan that leaves no time or energy for $\zeta$ will eventually erode $\phi$.

$\eta$ is signed: positive when a choice feels net good day to day, negative when it does not. Many decisions carry emotional weight beyond their financial weight. Emotions also run both ways: meaningful work can produce pride, autonomy can produce relief, good company can produce energy, while a draining job pays in chronic stress, a wrong roommate pays in friction, and a stretched purchase pays in anxiety. These effects are real even when they do not appear on a balance sheet.

| Choice | Possible emotional impact |
|---|---|
| Stay at home | Ease and savings, against privacy loss, conflict, and feeling stuck |
| Move out | Sense of freedom and ownership, against financial pressure, isolation, and household labor |
| Long-hour job | Pride in earning and progress, against chronic stress, fatigue, and lost rest |
| Intensive training | Sense of growth and identity, against discipline cost, delayed gratification, and self-doubt |
| Car ownership | Mobility, freedom, pride of ownership, against maintenance anxiety and commute fatigue |

$\nu$ measures the network of people you depend on, contribute to, and grow with: family, close friends, romantic partners, mentors, and community. People are not interchangeable, and a thin network is a real fragility. The same shock that someone with strong relationships can absorb can flatten someone who is alone. Many plans look efficient on paper but quietly damage $\nu$. Long hours leave no time for friends. A move can sever a community before a new one forms. Some damage is reversible. Some is not.

$\phi$, $\psi$, and $\nu$ are floors in the viable filter. $\zeta$ and $\eta$ contribute to momentum but are not hard floors: a plan can briefly skip exercise or feel hard without becoming nonviable. They become floors implicitly when sustained low values destroy $\phi$ or $\psi$.

> No plan is a good plan if it ruins your body, your mind, or your closeness to the people who matter. Feeling bad for a stretch is survivable. Staying broken is not.

### 3.2 Cross-Variable Relationships

Why model relationships between dimensions at all? Because the dimensions are not actually independent. Education does cost time and money. Field-level technology shifts do affect income. Without these connections, the model is a list of categories rather than a working system that can estimate what a candidate decision will produce. The estimates are approximations, not predictions; they exist to support comparison, not to forecast.

Education's sub-components connect to time, assets, and projected income through four formal relationships:

- $\tau$ (training time) reduces $p$ during the training period. While training is in progress, $p_{actual} = p_{baseline} - \tau_{weekly}$. After training ends, $p$ returns to baseline.
- $\mu$ (training money) subtracts from $\sigma$ at training start, or amortizes across the training horizon.
- $\rho$ (completion risk) discounts the expected post-training income gain. A 30 percent risk of not completing a credential discounts the expected $\Delta y$ by 30 percent.
- $\hat{y}(L_s, H)$ projects current income forward over the planning horizon, combining personal growth $\gamma$ and field-level technology trajectory $\delta$. The projection is what makes a stagnant $K$ in a declining field actually fail desirability: even if $y_s \geq y_{min}$ today, projected $\hat{y}$ falls below the threshold within $H$ years if $\delta$ is sufficiently negative.

Emotional comparison between alternatives uses the difference of net emotional impacts: a choice becomes more attractive as $\eta(\text{this}) - \eta(\text{alternative})$ rises. Because $\eta$ is signed, this works in both directions: a less-bad alternative is more attractive than a worse one, and a more-good option is more attractive than a less-good one.

### 3.3 Viable and Desirable

Why two filters and not one? Because survival is not the same as flourishing. A plan can be technically possible but actually awful to live. Without the distinction, the model could rank a barely-surviving plan above a comfortable one because the surviving plan looked busy. The viable filter rules out plans that break you. The desirable filter rules in plans that support a life worth wanting.

Two filters separate plans by quality.

$L_{viable}$ contains life-states that survive: nonnegative cash flow, sufficient risk buffer, all three time dimensions above their floors, and physical, mental, and relational health above their floors. Failing any of these means the plan is nonviable, regardless of how attractive it looks elsewhere.

$L_{desirable}$ is a strict subset of $L_{viable}$. A desirable life-state additionally has each independence type meeting its minimum, named values ($e$, $g$, $\beta$) above their floors, current and projected income meeting $y_{min}$, positive net worth ($\sigma \geq d$), and fitness and emotional impact above their floors.

The distinction matters because a plan that feels exciting but creates a brittle life is filtered out as nonviable before any momentum comparison happens. Among viable plans, only desirable ones produce a life worth wanting.

Scenario filters $S_{viable}$ and $S_{desirable}$ apply these same predicates to the life-state $L_s$ that each scenario $s$ produces.

### 3.4 Adjustable

Why a policy rather than a fixed plan? Because the future cannot be predicted in detail. New information will arrive (a job offer, an injury, a relationship, a market shift) and a plan committed years in advance will be out of date by the time it gets executed. Treating the model as a policy means you use it again at each stage, with whatever you have actually learned.

The path is not chosen once. You apply the model at each stage, using current information to choose the next step, observe the result, and apply the model again from your new life-state.

For the path to remain adjustable, individual decisions must stay reversible enough that future redirection is possible. State-level resilience is handled by the viable-state floors (a state above its floors can absorb shocks; a state at its floors cannot). How recoverable each decision is determines whether the path stays adjustable.

$R(s_j) \in [0, 1]$ measures how recoverable decision $s_j$ is, computed from three dimensions. $\lambda_j$ is lock-in duration as a fraction of the planning horizon (a 12-month lease over a 5-year horizon has $\lambda \approx 0.2$). $\xi_j$ is exit cost as a fraction of savings (breaking a lease for two months' rent on $10,000 in savings has $\xi \approx 0.1$). $\Delta_j$ is state disruption: roughly the fraction of $L$'s sub-components materially changed by the decision.

Examples:

| Decision | $\lambda$ | $\xi$ | $\Delta$ | $R$ |
|---|---:|---:|---:|---:|
| Try a part-time job | 0.05 | 0.00 | 0.10 | 0.95 |
| Take a short course | 0.10 | 0.05 | 0.15 | 0.90 |
| Sign a 12-month lease (5-yr horizon) | 0.20 | 0.10 | 0.40 | 0.77 |
| Take on high-interest debt | 0.50 | 0.30 | 0.50 | 0.57 |
| Buy a car that drains $r$ | 0.30 | 0.50 | 0.40 | 0.60 |

A plan should satisfy $R(s_j) \geq R_{min}$ for each step $j$ where the decision is large enough that an error would meaningfully change the path. A decision with low $R$ removes future options regardless of how good it looks in the moment.

As stages elapse, the remaining horizon shrinks. Each iteration of the re-optimization is bounded by the time still available, not the full $H$. A path that consumed half its horizon getting to stage $j$ has only the other half left to reach a desirable terminal state.

Being adjustable and being falsifiable are different responses to new information. An adjustable path adjusts within the existing model. A falsifiable model adjusts itself when reality stops fitting it. A path that needs frequent adjustment is not necessarily a sign that the model is wrong. A model that produces consistently poor adjustments is.

> Prefer decisions you can step back from. Irreversible decisions need more evidence than reversible ones.

### 3.5 Momentum and Path Objective

Why reduce the life-state to a single number? Because you need to compare options, and comparison requires reduction. Many things matter, and they matter differently. Momentum is the weighted sum that lets the model say one path scores higher than another without dropping any of the components that built the score. The score is a comparison aid, not a verdict.

Momentum scores a life-state. Path momentum scores a path. The path objective combines the scoring with the constraints from previous sections.

#### Time directed at enjoyment

The leading term in $Momentum(L)$ is the cross-product $w_{qe} \cdot q \cdot e$. This is the formal counterpart of the conjecture's "time directed at enjoyment." The cross-product requires both energy quality and enjoyment to be high for the term to contribute meaningfully. High-quality time spent stressed scores low because $e$ is low. Low-energy time spent attempting to enjoy scores low because $q$ is low. Only time that is both high-quality and enjoyable scores high.

When path momentum duration-weights this term, the resulting quantity is $w_{qe} \cdot \sum_j d_j \cdot q_j \cdot e_j$, literally "time times quality times enjoyment summed over the path." The asymmetry in joint optimization is intentional: with $w_q = 4$, $w_e = 3$, $w_{qe} = 5$, the contribution at $(q=1, e=1)$ is 12 while either alone scores only 3 or 4. Joint alignment is rewarded.

#### Goal modifies difficulty

The additive sum of $g$ (goal progress) and $\eta$ (emotional impact) implements the conjecture's claim that the goal modifies the difficulty. Hardship pursued toward a wanted outcome appears as positive $g$ outweighing negative $\eta$ in the sum, netting positive contribution. Hardship endured without progress appears as zero or negative $g$ alongside negative $\eta$, netting negative contribution. The harmonization is in the weights, not in a separate coupling term.

#### Weights

The weights are person-specific importances. Time-related variables ($p$, $b$, $q$) and the time-enjoyment coupling carry high weights because time is the most valuable resource. Cash flow, risk buffer, stability, and the three health floors also carry high weights because their collapse makes the whole life-state fragile.

$K$'s sub-components do not appear in the score directly because their effect already shows up in $y$, $\sigma$, $p$, and the horizon condition. $d$ enters negatively through cash flow and the net-worth condition.

| Variable | Meaning | Suggested Weight |
|---|---|---:|
| $q \cdot e$ | Time directed at enjoyment | 5 |
| $i_1$ | Mobility independence | 2 |
| $i_2$ | Financial independence | 3 |
| $i_3$ | Residential independence | 2 |
| $i_4$ | Decision independence | 2 |
| $e$ | Enjoyable life | 3 |
| $g$ | Goal progress | 3 |
| $\beta$ | Stability / emotional safety | 4 |
| $p$ | Productive time | 4 |
| $b$ | Buffer time | 4 |
| $q$ | Quality of time | 4 |
| $c$ | Cash flow | 4 |
| $\sigma$ | Savings | 3 |
| $r$ | Risk buffer | 4 |
| $y$ | Income | 3 |
| $\gamma$ | Income growth | 2 |
| $\phi$ | Physical health | 4 |
| $\psi$ | Mental health | 4 |
| $\zeta$ | Fitness | 2 |
| $\eta$ | Emotional impact | 3 |
| $\nu$ | Relational quality | 4 |

The best single scenario is the desirable scenario with the highest momentum. Selecting from $S_{desirable}$ rather than $S_{viable}$ aligns the single-scenario optimum with the path-level objective: both demand a life-state worth wanting, not merely one that survives.

#### Paths and the journey

Your life is a sequence of life-states, not a single decision. A path $P = (s_0, s_1, \dots, s_n)$ is a sequence of scenarios over time, each producing its own life-state.

Example scenarios (illustrative, not prescriptive):

| Scenario | Description |
|---|---|
| $s_1$ | Stay with family, buy no car, save aggressively |
| $s_2$ | Stay with family, buy modest car, preserve savings buffer |
| $s_3$ | Move out, buy car |
| $s_4$ | Move out, no car |
| $s_5$ | Stay low-rent, buy reliable modest car, pursue income/credential path, move out later |
| $s_6$ | Work more hours immediately, save more money, delay car purchase |
| $s_7$ | Keep current work, add training or school, delay apartment independence |

A path's quality is judged by the lived experience across its stages, weighted by how long each stage lasts. Scoring across stages rather than only at the endpoint reflects that the journey is what you live. A path that reaches the same destination through better intermediate states is a better path. Stage durations $d_j$ weight the sum so that long stretches of a given life-state count more than brief ones; a year of stress is worse than a month of stress at the same intensity.

#### Horizon budget

$\sum_{j=0}^{n} d_j \leq H$ is what makes time the binding resource. A path cannot extend beyond the planning horizon $H$. Longer stages crowd out shorter ones. Scenarios that move toward desirable life-states quickly leave more horizon for further refinement; scenarios that linger consume the budget without progressing.

This is the formalization of the conjecture's "time is finite and spent whether or not you choose where it goes." Even a path with strong per-stage momentum fails if it runs out of horizon before reaching a desirable terminal life-state.

#### Constraints

The path objective is to maximize path momentum subject to four constraints. Each constraint corresponds to a piece of the conjecture:

- The terminal life-state is desirable ($L_n \in L_{desirable}$): momentum points toward something more desirable, not merely something survivable.
- Every intermediate life-state is viable ($L_j \in L_{viable}$): the journey is what you live, and a journey through nonviable states is not actually lived through.
- Every large decision is recoverable enough ($R(s_j) \geq R_{min}$): an adjustable path requires reversible decisions.
- The total stage durations fit the horizon ($\sum_j d_j \leq H$): time is finite.

### 3.6 Falsifiability

Why include this section at all? Because the model could be wrong. The five dimensions might miss something important. The weights might be miscalibrated. The horizon projection might fit reality poorly. A model used as if it were truth would lock you into bad decisions when reality drifts from the model. A model treated as a conjecture stays useful by getting revised.

The model is itself a conjecture and should be revisable. Conditions that should trigger revision:

- A scenario produces high momentum but feels emotionally wrong. (A value is missing or mis-weighted.)
- A scenario looks viable on paper but fails repeatedly in practice. (A constraint is uncosted.)
- Your stated values shift in a stable, considered way. ($V$ needs updating.)
- A variable in $L$ turns out to be redundant, or a needed variable is missing.
- The weights in $Momentum$ produce rankings that contradict considered judgment across many scenarios.
- The horizon-projected income $\hat{y}$ produces predictions that are repeatedly wrong by large margins. (The functional form, or $\delta$ or $\gamma$ estimates, may need revision.)

> The model is a tool for thinking, not a verdict. When it stops fitting reality, change the model.
