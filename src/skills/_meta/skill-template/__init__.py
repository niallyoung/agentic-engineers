# <skill-name> skill package
#
# Replace <skill-name> and SkillBase with the actual skill name and class.
# This __init__.py exports the public API of the skill so callers can use:
#
#   from src.skills.skill_name import SkillBase
#
# Only export symbols that are part of the public API. Internal helpers should
# remain private (underscore-prefixed) in the scripts/ sub-package.
#
# USAGE AFTER COPYING:
#   1. Rename this file's target package from skill_name to your_skill_name
#   2. Rename SkillBase to your actual class name
#   3. Remove the comments above

# TODO: uncomment and update the import below
# from .scripts.skill_name import SkillBase  # noqa: F401
#
# __all__ = ["SkillBase"]
