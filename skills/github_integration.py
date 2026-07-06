def run(action, repo=None, **kwargs):
    gh = sdk["github"]
    if action == "list_open_issues":
        return gh.list_open_issues(repo, label=kwargs.get("label"))
    if action == "get_issue":
        return gh.get_issue(repo, kwargs["number"])
    if action == "create_issue":
        return gh.create_issue(repo, kwargs["title"], kwargs.get("body", ""), kwargs.get("labels"))
    if action == "add_comment":
        return gh.add_comment(repo, kwargs["number"], kwargs["body"])
    if action == "update_issue":
        return gh.update_issue(
            repo,
            kwargs["number"],
            title=kwargs.get("title"),
            body=kwargs.get("body"),
            labels=kwargs.get("labels"),
            state=kwargs.get("state"),
        )
    if action == "create_label":
        return gh.create_label(
            repo, kwargs["name"], kwargs.get("color", "ededed"), kwargs.get("description", "")
        )
    if action == "close_issue":
        return gh.close_issue(repo, kwargs["number"])
    if action == "create_pr":
        return gh.create_pr(
            repo, kwargs["title"], kwargs.get("body", ""), kwargs["head"], kwargs.get("base", "main")
        )
    if action == "get_pr":
        return gh.get_pr(repo, kwargs["number"])
    if action == "get_pr_diff":
        return gh.get_pr_diff(repo, kwargs["number"])
    if action == "merge_pr":
        return gh.merge_pr(
            repo,
            kwargs["number"],
            merge_method=kwargs.get("merge_method", "squash"),
            commit_title=kwargs.get("commit_title"),
            commit_message=kwargs.get("commit_message"),
        )
    if action == "create_repo":
        return gh.create_repo(
            kwargs["name"], kwargs.get("description", ""), kwargs.get("private", True)
        )
    return {"error": f"Unknown action: {action}"}
