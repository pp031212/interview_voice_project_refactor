from langgraph.graph.state import CompiledStateGraph


def output_pic_graph(graph: CompiledStateGraph, filename: str = "graph.jpg") -> None:
    try:
        mermaid_code = graph.get_graph().draw_mermaid_png()
        with open(filename, "wb") as file_handle:
            file_handle.write(mermaid_code)
    except Exception as exc:  # noqa: BLE001
        print(exc)
