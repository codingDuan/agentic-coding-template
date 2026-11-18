.PHONY: help test-critical test-critical-scope test-workflow audit-plans

# test-critical：核心链路测试清单的唯一来源（RULES.md §8）。按项目填写下面的命令。
# 是否需要跑见 make test-critical-scope；SINCE=<sha> 可沿用一次全绿的运行。
TEST_CRITICAL_CMD ?=
PYTHON ?= python3

help:
	@echo "make test-critical        # run core-path tests — must stay green before merge"
	@echo "make test-critical-scope  # decide whether test-critical must run (RULES.md §8); SINCE=<sha> to reuse a green run"
	@echo "make test-workflow        # tests for the workflow itself: skill scripts + CI scope scripts"
	@echo "make audit-plans          # docs/plans structure and link audit"

# 工作流自身的测试：skill 自带脚本 + 路径分类脚本。改 skills/** 或 .github/scripts/** 后跑。
test-workflow:
	$(PYTHON) -m pytest -q skills
	@set -e; for t in .github/scripts/test-*.sh; do \
	  case "$$t" in */test-critical-scope.sh) continue ;; esac; \
	  echo "bash $$t"; bash "$$t"; \
	done

audit-plans:
	$(PYTHON) skills/organizing-plans/scripts/audit_plans.py --repo-root . --check

test-critical:
	@if [ -z "$(TEST_CRITICAL_CMD)" ]; then \
	  echo "test-critical is not configured: set TEST_CRITICAL_CMD in the Makefile (RULES.md §8)" >&2; exit 2; \
	fi
	$(TEST_CRITICAL_CMD)

test-critical-scope:
	bash .github/scripts/test-critical-scope.sh $(SINCE)
