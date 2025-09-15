
"""
Simple session helpers for logout, compatible with Streamlit's session_state.
"""
def logout(session_state: dict):
    keys = list(session_state.keys())
    for k in keys:
        del session_state[k]
    session_state["logged_out_at"] = __import__("time").time()
    return True
