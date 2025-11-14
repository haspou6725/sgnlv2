#!/bin/bash
# SGNL-V2 Setup Verification Script
# Checks if all components are properly configured

echo "=============================================="
echo "SGNL-V2 Setup Verification"
echo "=============================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check counter
CHECKS_PASSED=0
CHECKS_TOTAL=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((CHECKS_PASSED++))
    ((CHECKS_TOTAL++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((CHECKS_TOTAL++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Check Python version
echo "1. Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    if [[ "$PYTHON_VERSION" > "3.10" ]] || [[ "$PYTHON_VERSION" == "3.10"* ]]; then
        check_pass "Python version: $PYTHON_VERSION"
    else
        check_fail "Python version $PYTHON_VERSION (need 3.10+)"
    fi
else
    check_fail "Python3 not found"
fi

# 2. Check file structure
echo ""
echo "2. Checking project structure..."
REQUIRED_FILES=(
    "app/main.py"
    "app/orchestrator.py"
    "data_fetcher/fetch_binance.py"
    "features/orderflow.py"
    "scalp_engine/scorer.py"
    "telegram_bot/notifier.py"
    "ui/dashboard.py"
    "storage/db.py"
    "requirements.txt"
    "docker-compose.yml"
    "Dockerfile"
    ".env.example"
    "README.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        check_pass "$file exists"
    else
        check_fail "$file missing"
    fi
done

# 3. Check .env configuration
echo ""
echo "3. Checking environment configuration..."
if [ -f ".env" ]; then
    check_pass ".env file exists"
    
    # Check for required variables
    if grep -q "TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here" .env; then
        check_warn "TELEGRAM_BOT_TOKEN not configured (using default)"
    else
        check_pass "TELEGRAM_BOT_TOKEN is configured"
    fi
    
    if grep -q "TELEGRAM_CHAT_ID=your_telegram_chat_id_here" .env; then
        check_warn "TELEGRAM_CHAT_ID not configured (using default)"
    else
        check_pass "TELEGRAM_CHAT_ID is configured"
    fi
else
    check_fail ".env file missing (copy from .env.example)"
fi

# 4. Check Docker availability (optional)
echo ""
echo "4. Checking Docker (optional)..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
    check_pass "Docker installed: $DOCKER_VERSION"
    
    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | tr -d ',')
        check_pass "Docker Compose installed: $COMPOSE_VERSION"
    else
        check_warn "Docker Compose not found (optional for deployment)"
    fi
else
    check_warn "Docker not installed (optional for deployment)"
fi

# 5. Check Python dependencies (if in venv)
echo ""
echo "5. Checking Python dependencies..."
if [ -d "venv" ]; then
    check_pass "Virtual environment exists"
else
    check_warn "No virtual environment found (recommended to create one)"
fi

# Check if key packages are available
if python3 -c "import aiohttp" 2>/dev/null; then
    check_pass "aiohttp installed"
else
    check_warn "aiohttp not installed (run: pip install -r requirements.txt)"
fi

if python3 -c "import loguru" 2>/dev/null; then
    check_pass "loguru installed"
else
    check_warn "loguru not installed (run: pip install -r requirements.txt)"
fi

# 6. Check directories
echo ""
echo "6. Checking required directories..."
if [ ! -d "logs" ]; then
    mkdir -p logs
    check_pass "Created logs directory"
else
    check_pass "logs directory exists"
fi

if [ ! -d "storage" ]; then
    mkdir -p storage
    check_pass "Created storage directory"
else
    check_pass "storage directory exists"
fi

# 7. Syntax check on key files
echo ""
echo "7. Checking Python syntax..."
KEY_FILES=(
    "app/main.py"
    "app/orchestrator.py"
    "scalp_engine/scorer.py"
)

for file in "${KEY_FILES[@]}"; do
    if python3 -m py_compile "$file" 2>/dev/null; then
        check_pass "$file syntax OK"
    else
        check_fail "$file has syntax errors"
    fi
done

# 8. Run tests (if pytest available)
echo ""
echo "8. Running tests..."
if command -v pytest &> /dev/null; then
    if pytest tests/ -v --tb=short &>/dev/null; then
        check_pass "All tests passed"
    else
        check_fail "Some tests failed (run: pytest tests/ -v)"
    fi
else
    check_warn "pytest not installed (run: pip install pytest pytest-asyncio)"
fi

# Summary
echo ""
echo "=============================================="
echo "Verification Summary"
echo "=============================================="
echo "Checks passed: $CHECKS_PASSED / $CHECKS_TOTAL"
echo ""

if [ $CHECKS_PASSED -eq $CHECKS_TOTAL ]; then
    echo -e "${GREEN}✓ All checks passed! Ready to deploy.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Edit .env with your Telegram credentials"
    echo "  2. Run: docker-compose up -d"
    echo "  3. Access dashboard: http://localhost:8501"
    exit 0
elif [ $CHECKS_PASSED -gt $((CHECKS_TOTAL * 3 / 4)) ]; then
    echo -e "${YELLOW}⚠ Most checks passed. Review warnings above.${NC}"
    exit 0
else
    echo -e "${RED}✗ Several checks failed. Fix errors before deploying.${NC}"
    exit 1
fi
