from dataclasses import dataclass, field
from typing import List, Optional, Dict

# -----------------------------
# Shared state object
# -----------------------------
@dataclass
class ReleasePipelineState:
    release_date: Optional[str] = None
    intent: Optional[str] = None  # INFO | CREATE_TOKEN | TAX
    selected_vesting_date: Optional[str] = None

    token_id: Optional[str] = None
    pipeline_stage: str = "INIT"
    participants_count: Optional[int] = None
    grants_count: Optional[int] = None

    fmv: Optional[float] = None
    sale_price: Optional[float] = None
    fmv_provided: bool = False
    sale_price_provided: bool = False

    errors: List[str] = field(default_factory=list)


# -----------------------------
# Tools (API wrappers)
# -----------------------------
def get_vesting_dates(participant_group_id: str) -> List[str]:
    """Return list of vesting dates"""
    # Call the vesting date API
    return ["2026-03-15", "2026-06-15", "2026-09-15"]


def create_token_via_vesting_details(vesting_date: str) -> Dict:
    """Creates the token for the vesting date"""
    return {
        "token_id": f"tok_{vesting_date.replace('-', '')}",
        "participants_count": 418,
        "grants_count": 912
    }


def update_fmv_sale_price(token_id: str, fmv: float, sale_price: float):
    """Updates FMV and Sale Price in token file"""
    print(f"Updated token {token_id} with FMV={fmv}, SP={sale_price}")


def calculate_tax(token_id: str):
    """Calculates tax for token"""
    print(f"Calculated tax for token {token_id}")


def lookup_existing_token(release_date: str) -> Optional[Dict]:
    """Check if a token already exists"""
    # Example: simulate no existing token
    return None
    # Could return: {"token_id": "...", "pipeline_stage": "FMV_UPDATED"}


# -----------------------------
# Agent nodes (cognitive)
# -----------------------------
def llm_parse_query(user_query: str):
    """Simulate LLM parsing for intent + params"""
    # For example purposes
    intent = "TAX" if "simulate" in user_query or "tax" in user_query else "INFO"
    release_date = None  # Assume next vesting by default
    fmv = 10 if "FMV 10" in user_query else None
    sale_price = 11 if "SP 11" in user_query else None
    return intent, release_date, fmv, sale_price


def interpret_user_query(state: ReleasePipelineState, user_query: str):
    intent, release_date, fmv, sale_price = llm_parse_query(user_query)
    state.intent = intent
    state.release_date = release_date
    if fmv:
        state.fmv = fmv
        state.fmv_provided = True
    if sale_price:
        state.sale_price = sale_price
        state.sale_price_provided = True
    return state


def resolve_idempotency(state: ReleasePipelineState, existing_token: Optional[Dict]):
    if not existing_token:
        state.pipeline_stage = "INIT"
        return state
    state.token_id = existing_token["token_id"]
    state.pipeline_stage = existing_token["pipeline_stage"]
    return state


def select_vesting_date(vesting_dates: List[str]) -> str:
    # For simplicity: choose the earliest
    return min(vesting_dates)


def decide_fmv_and_sale_price(state: ReleasePipelineState):
    if not state.fmv_provided or not state.sale_price_provided:
        raise ValueError("FMV and Sale Price are required to calculate tax")
    return state


def tax_readiness_check(state: ReleasePipelineState):
    if not (state.fmv_provided and state.sale_price_provided):
        state.errors.append("FMV or Sale Price missing")
        raise RuntimeError("Cannot calculate tax")
    return state


# -----------------------------
# ReleasePipelineAgent
# -----------------------------
class ReleasePipelineAgent:
    def __init__(self):
        pass

    def run(self, state: ReleasePipelineState, user_query: str):
        # 1. Interpret user query
        state = interpret_user_query(state, user_query)

        # 2. Idempotency check
        existing = lookup_existing_token(state.release_date or "")
        state = resolve_idempotency(state, existing)

        # 3. Ensure token exists
        if state.pipeline_stage == "INIT":
            vesting_dates = get_vesting_dates("default_group")
            state.selected_vesting_date = select_vesting_date(vesting_dates)
            token_info = create_token_via_vesting_details(state.selected_vesting_date)
            state.token_id = token_info["token_id"]
            state.participants_count = token_info["participants_count"]
            state.grants_count = token_info["grants_count"]
            state.pipeline_stage = "TOKEN_CREATED"

        # 4. Tax flow
        if state.intent == "TAX":
            # FMV/SP update
            if state.pipeline_stage == "TOKEN_CREATED":
                state = decide_fmv_and_sale_price(state)
                update_fmv_sale_price(
                    token_id=state.token_id,
                    fmv=state.fmv,
                    sale_price=state.sale_price
                )
                state.pipeline_stage = "FMV_UPDATED"

            # Tax calculation
            if state.pipeline_stage == "FMV_UPDATED":
                state = tax_readiness_check(state)
                calculate_tax(state.token_id)
                state.pipeline_stage = "TAX_CALCULATED"

        return state


# -----------------------------
# Batch mode wrapper
# -----------------------------
def run_batch(release_dates: List[str], user_query: str):
    agent = ReleasePipelineAgent()
    results = []

    for release_date in release_dates:
        state = ReleasePipelineState(release_date=release_date)
        try:
            result = agent.run(state, user_query)
            results.append({
                "release_date": release_date,
                "token_id": result.token_id,
                "stage": result.pipeline_stage
            })
        except Exception as e:
            results.append({
                "release_date": release_date,
                "error": str(e)
            })

    return results


# -----------------------------
# Example run
# -----------------------------
if __name__ == "__main__":
    user_query = "simulate next release for FMV 10 and SP 11"
    state = ReleasePipelineState()
    agent = ReleasePipelineAgent()
    final_state = agent.run(state, user_query)
    print(f"Final pipeline state: {final_state}")

    # Batch example
    batch_results = run_batch(["2026-03-15", "2026-06-15"], user_query)
    print("Batch results:", batch_results)
