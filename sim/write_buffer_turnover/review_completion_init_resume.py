"""Codex offline raw review for the fresh Task031 include-fix resume only."""
import simulation_completion_init_resume as resume
import review_completion as review

review.DESIGN, review.TAG = resume.DESIGN, resume.TAG
review.require_completion_inputs = resume.require_completion_inputs


if __name__ == '__main__':
    review.main()
