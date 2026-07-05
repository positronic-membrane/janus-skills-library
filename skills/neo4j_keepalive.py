def neo4j_keepalive():
    import src.config as config
    if not config.NEO4J_URI:
        return "Neo4j keep-alive skipped: NEO4J_URI is not configured."
    try:
        from src.epistemic import Neo4jKnowledgeStore
        Neo4jKnowledgeStore().run("RETURN 1")
    except Exception as e:
        sdk['logger'].error(
            f"Neo4j keep-alive failed: {e}. A keep-alive cannot resume a paused instance — "
            "if the Aura Free instance has auto-paused, resume it manually in the Neo4j Aura console "
            "before it is deleted (~30 days paused)."
        )
        return f"Neo4j keep-alive FAILED: {e}"
    return "Neo4j keep-alive succeeded."
