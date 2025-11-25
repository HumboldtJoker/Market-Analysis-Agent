"""
Collaborative Dialogue Agent for AutoInvestor

Extends ReAct agent with human-AI collaborative decision-making.
Implements the Coalition philosophy: augmentation over replacement.

After analysis, agent proposes strategic questions for human context/intuition,
then synthesizes a refined recommendation incorporating human input.

Author: Lyra & Thomas
Version: 1.0.0 - 2025-11-25
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from autoinvestor_react import ReActAgent


class CollaborativeAgent(ReActAgent):
    """
    AI Investment Agent with Human-in-the-Loop Collaboration

    Extends ReActAgent with a dialogue phase between analysis and recommendation.
    Agent generates strategic questions based on findings, human provides context,
    agent synthesizes final recommendation incorporating both AI analysis and human insight.

    Philosophy: Augmentation over replacement - combining AI breadth with human depth.
    """

    def __init__(self, *args, **kwargs):
        """Initialize collaborative agent (same as ReActAgent)"""
        super().__init__(*args, **kwargs)
        self.dialogue_history = []

    def run_collaborative(self, user_query: str,
                         max_questions: int = 3,
                         verbose: bool = True,
                         auto_timeout: int = 60) -> Dict[str, Any]:
        """
        Run ReAct loop with collaborative dialogue phase

        Process:
        1. Agent analyzes using all available tools
        2. Agent generates strategic questions based on findings
        3. Human provides context/intuition
        4. Agent synthesizes final recommendation incorporating both perspectives

        Args:
            user_query: Investment question to research
            max_questions: Maximum number of questions to ask (1-5)
            verbose: Print progress to console
            auto_timeout: Seconds to wait for human input before auto-proceeding

        Returns:
            Dictionary with collaborative recommendation and metadata
        """
        # Phase 1: Standard ReAct analysis
        if verbose:
            print(f"\n{'='*80}")
            print(f"COLLABORATIVE ANALYSIS MODE")
            print(f"{'='*80}")
            print(f"\nQuery: {user_query}")
            print(f"\n[Phase 1] AI Analysis - gathering data and initial insights...")
            print(f"{'='*80}\n")

        # Run standard ReAct loop but don't finalize answer yet
        analysis_result = self._run_analysis_phase(user_query, verbose=verbose)

        if not analysis_result['success']:
            return analysis_result

        # Phase 2: Generate strategic questions
        if verbose:
            print(f"\n{'='*80}")
            print(f"[Phase 2] Collaborative Dialogue - seeking human context...")
            print(f"{'='*80}\n")

        questions = self._generate_strategic_questions(
            user_query,
            analysis_result,
            max_questions=max_questions
        )

        if verbose:
            print(f"Based on my analysis, I have {len(questions)} strategic questions:\n")
            for i, q in enumerate(questions, 1):
                print(f"\n{i}. {q['question']}")
                print(f"   Context: {q['context']}")
                print(f"   Why I'm asking: {q['rationale']}")

        # Phase 3: Collect human input
        if verbose:
            print(f"\n{'='*80}")
            print(f"Please provide your insights (or press Enter to skip):")
            print(f"{'='*80}\n")

        human_responses = self._collect_human_input(questions, verbose=verbose)

        # Phase 4: Synthesize collaborative recommendation
        if verbose:
            print(f"\n{'='*80}")
            print(f"[Phase 3] Synthesis - integrating AI analysis with human insight...")
            print(f"{'='*80}\n")

        final_recommendation = self._synthesize_collaborative_answer(
            user_query,
            analysis_result,
            questions,
            human_responses,
            verbose=verbose
        )

        return {
            "success": True,
            "answer": final_recommendation['answer'],
            "collaborative_mode": True,
            "ai_analysis": analysis_result['preliminary_answer'],
            "questions_asked": questions,
            "human_responses": human_responses,
            "synthesis_rationale": final_recommendation['rationale'],
            "iterations": analysis_result['iterations'],
            "history": self.history,
            "dialogue_history": self.dialogue_history,
            "timestamp": datetime.now().isoformat()
        }

    def _run_analysis_phase(self, user_query: str, verbose: bool = True) -> Dict:
        """
        Run ReAct analysis phase (gather data, don't finalize yet)
        """
        self.history = []

        for iteration in range(self.max_iterations):
            system_prompt = self._build_system_prompt()

            if iteration == 0:
                user_prompt = f"""USER QUERY: {user_query}

Conduct thorough research using available tools. After gathering sufficient data,
think about strategic questions you'd want to ask a human investor before making
a final recommendation. DO NOT provide FINAL_ANSWER yet - I'll ask for that after
we discuss together.

Begin your research:"""
            else:
                user_prompt = self._format_history_for_prompt() + """

Continue your research. Remember: gather data first, questions for human later."""

            if verbose and iteration > 0:
                print(f"\n--- Iteration {iteration + 1} ---")

            # Get response from Claude
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            response = message.content[0].text
            thought, action, action_input = self._parse_response(response)

            if verbose and thought:
                print(f"\nThought: {thought}")

            if thought:
                self.history.append({
                    "type": "thought",
                    "content": thought,
                    "iteration": iteration
                })

            # Execute action (if not FINAL_ANSWER)
            if action and action.upper() != "FINAL_ANSWER":
                if verbose:
                    print(f"Action: {action}")
                    print(f"Input: {action_input}")

                self.history.append({
                    "type": "action",
                    "tool": action,
                    "input": action_input,
                    "iteration": iteration
                })

                # Execute tool
                observation = self._execute_tool(action, action_input)

                if verbose:
                    obs_preview = observation[:200] + "..." if len(observation) > 200 else observation
                    print(f"Observation: {obs_preview}\n")

                self.history.append({
                    "type": "observation",
                    "content": observation,
                    "iteration": iteration
                })

            elif action and action.upper() == "FINAL_ANSWER":
                # Agent tried to finalize early - extract preliminary insights instead
                return {
                    "success": True,
                    "preliminary_answer": action_input,
                    "iterations": iteration + 1
                }

        # Max iterations reached - extract what we have
        last_thought = next((h for h in reversed(self.history) if h["type"] == "thought"), None)
        preliminary = last_thought["content"] if last_thought else "Analysis incomplete"

        return {
            "success": True,
            "preliminary_answer": preliminary,
            "iterations": self.max_iterations
        }

    def _generate_strategic_questions(self, user_query: str,
                                     analysis_result: Dict,
                                     max_questions: int = 3) -> List[Dict]:
        """
        Generate strategic questions for human based on AI analysis

        Questions focus on:
        - Human context/insider knowledge
        - Risk tolerance and preferences
        - Sector-specific insights
        - Timing and market sentiment
        """
        # Build context from analysis history
        analysis_summary = self._summarize_analysis()

        prompt = f"""Based on my analysis of: {user_query}

ANALYSIS SUMMARY:
{analysis_summary}

PRELIMINARY INSIGHT:
{analysis_result['preliminary_answer']}

I need to generate {max_questions} strategic questions for the human investor that would
help refine my recommendation. Focus on areas where human context, intuition, or
preferences would add value that pure data analysis cannot provide.

For each question, provide:
1. The question itself
2. Why this question matters given the data
3. Brief context about what I found

Format as JSON array:
[
  {{
    "question": "specific strategic question",
    "context": "what my analysis revealed",
    "rationale": "why human insight adds value here"
  }},
  ...
]

Generate questions now:"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            system="You are an AI investment analyst collaborating with a human. Generate strategic questions.",
            messages=[{"role": "user", "content": prompt}]
        )

        response = message.content[0].text.strip()

        # Extract JSON from response
        try:
            # Find JSON array in response
            start = response.find('[')
            end = response.rfind(']') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                questions = json.loads(json_str)
                return questions[:max_questions]
        except:
            pass

        # Fallback: generic questions
        return [
            {
                "question": "What's your current view on market conditions for this sector?",
                "context": "My analysis shows mixed technical signals",
                "rationale": "Your market sentiment reading could help weight these signals"
            },
            {
                "question": "Do you have any sector-specific knowledge or concerns not reflected in public data?",
                "context": "Public financials look solid",
                "rationale": "Industry insider knowledge often precedes public disclosures"
            },
            {
                "question": "How does this fit with your overall portfolio strategy and risk tolerance?",
                "context": "This represents moderate risk with growth potential",
                "rationale": "Portfolio context determines appropriate position sizing"
            }
        ][:max_questions]

    def _collect_human_input(self, questions: List[Dict],
                            verbose: bool = True) -> List[Dict]:
        """
        Collect human responses to strategic questions

        Returns list of {question, response} dicts
        """
        responses = []

        for i, q in enumerate(questions, 1):
            if verbose:
                response = input(f"\nQ{i}> ").strip()
            else:
                response = ""  # Silent mode for testing

            responses.append({
                "question": q['question'],
                "context": q['context'],
                "response": response if response else "[No response provided]",
                "skipped": not bool(response)
            })

            self.dialogue_history.append({
                "question_num": i,
                "question": q['question'],
                "response": response,
                "timestamp": datetime.now().isoformat()
            })

        return responses

    def _synthesize_collaborative_answer(self, user_query: str,
                                        analysis_result: Dict,
                                        questions: List[Dict],
                                        responses: List[Dict],
                                        verbose: bool = True) -> Dict:
        """
        Synthesize final recommendation incorporating AI analysis + human input
        """
        # Build synthesis prompt
        analysis_summary = self._summarize_analysis()

        dialogue_summary = "\n".join([
            f"Q: {r['question']}\nHuman: {r['response']}"
            for r in responses
        ])

        prompt = f"""INVESTMENT QUERY: {user_query}

MY ANALYSIS:
{analysis_summary}

PRELIMINARY INSIGHT:
{analysis_result['preliminary_answer']}

COLLABORATIVE DIALOGUE:
{dialogue_summary}

Now provide a FINAL RECOMMENDATION that:
1. Synthesizes my data analysis with the human's contextual insights
2. Shows how the human input shaped or refined my conclusion
3. Attributes insights appropriately ("Based on your [X]...", "You mentioned [Y], which...")
4. Provides clear actionable recommendation

Use this format:
SYNTHESIS:
[How AI analysis + human insight combine]

FINAL RECOMMENDATION:
[Clear buy/sell/hold with reasoning]

ATTRIBUTION:
[How human input influenced the decision]

Provide final answer now:"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system="You are an AI investment analyst providing collaborative recommendations.",
            messages=[{"role": "user", "content": prompt}]
        )

        final_answer = message.content[0].text.strip()

        if verbose:
            print(f"\n{'='*80}")
            print("COLLABORATIVE RECOMMENDATION:")
            print(f"{'='*80}\n")
            print(final_answer)
            print(f"\n{'='*80}")

        # Extract sections
        synthesis = ""
        recommendation = ""
        attribution = ""

        lines = final_answer.split('\n')
        current_section = None

        for line in lines:
            if 'SYNTHESIS:' in line.upper():
                current_section = 'synthesis'
            elif 'FINAL RECOMMENDATION:' in line.upper() or 'RECOMMENDATION:' in line.upper():
                current_section = 'recommendation'
            elif 'ATTRIBUTION:' in line.upper():
                current_section = 'attribution'
            elif current_section == 'synthesis':
                synthesis += line + '\n'
            elif current_section == 'recommendation':
                recommendation += line + '\n'
            elif current_section == 'attribution':
                attribution += line + '\n'

        return {
            "answer": final_answer,
            "synthesis": synthesis.strip(),
            "recommendation": recommendation.strip(),
            "attribution": attribution.strip(),
            "rationale": f"Collaborative decision combining AI analysis across {analysis_result['iterations']} iterations with human insights on {len([r for r in responses if not r['skipped']])} strategic questions."
        }

    def _summarize_analysis(self) -> str:
        """Create concise summary of analysis history"""
        tools_used = set()
        key_findings = []

        for item in self.history:
            if item["type"] == "action":
                tools_used.add(item["tool"])
            elif item["type"] == "observation":
                # Extract first 150 chars as key finding
                obs = item["content"][:150].strip()
                if obs:
                    key_findings.append(obs)

        summary = f"Tools used: {', '.join(tools_used)}\n\n"
        summary += "Key findings:\n"
        for finding in key_findings[:5]:  # Top 5 findings
            summary += f"- {finding}...\n"

        return summary


if __name__ == "__main__":
    """Demo collaborative analysis"""
    import sys

    # Initialize agent
    agent = CollaborativeAgent(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        max_iterations=10
    )

    # Register basic tools (in real usage, register all tools)
    from autoinvestor_react import Tool, get_stock_price, get_company_financials

    agent.tools.register(Tool(
        name="get_stock_price",
        description="Get current stock price and trading data",
        parameters={"ticker": "string"},
        function=get_stock_price
    ))

    agent.tools.register(Tool(
        name="get_company_financials",
        description="Get company financial statements",
        parameters={"ticker": "string"},
        function=get_company_financials
    ))

    # Run collaborative analysis
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Should I invest in AAPL right now?"

    result = agent.run_collaborative(
        query,
        max_questions=3,
        verbose=True
    )

    print(f"\n\nCollaborative analysis complete!")
    print(f"Questions asked: {len(result['questions_asked'])}")
    print(f"Human responses: {len([r for r in result['human_responses'] if not r['skipped']])}")
