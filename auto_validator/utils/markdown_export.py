from auto_validator.models.project import ProjectState


def export_to_markdown(state: ProjectState) -> str:
    """Render a full project state as a clean Markdown document."""
    lines = [
        f"# Auto-Validator Report: {state.idea}",
        f"",
        f"**Project ID:** `{state.project_id}`  ",
        f"**Status:** {state.status.value}  ",
        f"**Created:** {state.created_at[:19]}",
        "",
    ]

    if state.strategist_output:
        s = state.strategist_output
        lines += [
            "---",
            "## Module A — Strategist",
            "",
            f"**Refined Idea:** {s.refined_idea}",
            "",
            f"### Chosen Angle: {s.chosen_angle.type.upper()}",
            f"**Headline:** {s.chosen_angle.headline}",
            f"{s.chosen_angle.description}",
            f"**Target Audience:** {s.chosen_angle.target_audience}",
            "",
            "### Customer Avatar",
            f"**{s.avatar.name}** · {s.avatar.age_range} · {s.avatar.occupation}",
            "",
            "**Pain Points:**",
        ]
        for p in s.avatar.pain_points:
            lines.append(f"- {p}")
        lines += [
            "",
            f"**Desired Outcome:** {s.avatar.desired_outcome}",
            f"**Biggest Fear:** {s.avatar.biggest_fear}",
            f"**Psychographics:** {s.avatar.psychographics}",
            "",
            "### Timeless Equation",
            f"| Dimension | Score | Analysis |",
            f"|-----------|-------|----------|",
            f"| People    | {s.equation.people_score}/10 | {s.equation.people_analysis} |",
            f"| Problem   | {s.equation.problem_score}/10 | {s.equation.problem_analysis} |",
            f"| Solution  | {s.equation.solution_score}/10 | {s.equation.solution_analysis} |",
            f"| Message   | {s.equation.message_score}/10 | {s.equation.message_analysis} |",
            f"| **Pain**  | **{s.equation.pain_score}/10** | {s.equation.validation_notes} |",
            "",
        ]

    if state.creative_output:
        c = state.creative_output
        lines += [
            "---",
            "## Module B — Creative Studio",
            "",
            "### Facebook Ad Hooks",
            "",
        ]
        for hook in c.ad_hooks:
            lines.append(f"**Variation {hook.variation_number}** ({hook.angle_type}):")
            lines.append(f"> {hook.hook_text}")
            if hook.visual_prompt:
                lines.append(f"*Visual:* {hook.visual_prompt}")
            lines.append("")

        lp = c.landing_page
        lines += [
            "### Landing Page Copy",
            "",
            f"**Headline:** {lp.above_fold_headline}",
            f"**Subheadline:** {lp.above_fold_subheadline}",
            "",
            "**Problem Section:**",
            lp.problem_section,
            "",
            "**Desired Outcome Section:**",
            lp.desired_outcome_section,
            "",
            f"**CTA:** {lp.cta_text}",
            f"*{lp.cta_subtext}*",
            "",
            "### Quiz Questions",
            "",
        ]
        for q in c.quiz_questions:
            lines.append(f"**{q.question_id}** ({q.question_type.value}): {q.question_text}")
            if q.options:
                for opt in q.options:
                    lines.append(f"  - {opt}")
            lines.append("")

    if state.closer_output:
        cl = state.closer_output
        lines += [
            "---",
            "## Module D — Closer",
            "",
            "### Thank-You Email",
            f"**Subject:** {cl.thank_you_email.subject}",
            "",
            cl.thank_you_email.body_text,
            "",
        ]
        if cl.plf_sequence:
            lines += ["### PLF Launch Sequence", ""]
            for i, email in enumerate(cl.plf_sequence.as_list(), 1):
                lines += [
                    f"#### Email {i}: {email.subject}",
                    email.body_text,
                    "",
                ]

    return "\n".join(lines)
