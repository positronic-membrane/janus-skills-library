def run(sdk, args):
    message = args.get("message", "")
    sdk["logger"].info("echo_message called")
    return {"result": message}
