"""Codex reviews the new GRS resume; old failed result stays untouched."""
import run_grs_resume as resume
import review

review.run = resume.base


if __name__ == '__main__':
    review.main()
