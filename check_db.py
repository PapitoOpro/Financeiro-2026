from database import db
db._skip_rls = True

rows = db.buscar("""
    SELECT pid, state, wait_event_type, query, now() - query_start as duration
    FROM pg_stat_activity
    WHERE datname = current_database()
    AND state != 'idle'
    AND pid != pg_backend_pid()
    ORDER BY query_start
""")
if rows.empty:
    print("Nenhuma sessao travada")
else:
    for _, r in rows.iterrows():
        pid = r["pid"]
        state = r["state"]
        wait = r.get("wait_event_type", "")
        dur = r["duration"]
        q = str(r["query"])[:150]
        print(f"PID={pid} state={state} wait={wait} dur={dur}")
        print(f"  query: {q}")
