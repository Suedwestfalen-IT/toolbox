from pathlib import Path
import importlib.metadata
from functools import lru_cache

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from jinja2 import Template

import uvicorn
import yaml
import toolbox

#pylint: disable = missing-function-docstring

# config
web_config = {}
with open("./config.yml", "r", encoding="utf-8") as fh:
    web_config = yaml.safe_load(fh)

# templating
templates = Jinja2Templates(directory="toolbox/web/templates")

app = FastAPI()
tb = toolbox.Toolbox()

# static files
dist = importlib.metadata.distribution("bootstrap")
static_path = Path(dist.locate_file("bootstrap/dist"))
app.mount("/bootstrap", StaticFiles(directory=str(static_path)), name="bootstrap")
app.mount("/static", StaticFiles(directory="toolbox/web/static"), name="static")

@lru_cache(maxsize=None)
def toolbox_wrapper(module_class, **kwargs):

    toolbox_module_obj = tb.init_module(module_class, kwargs)
    return toolbox_module_obj.run()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "web_config": web_config})

@app.get("/{toolgroup}/{tool}", response_class=HTMLResponse)
def get_tool(toolgroup:str, tool:str, request: Request):
    return render_tool(toolgroup, tool, request)

@app.get("/{toolgroup}/{tool}/run", response_class=HTMLResponse)
def run_tool(toolgroup:str, tool:str, request: Request):
    return render_tool(toolgroup, tool, request, True)

def render_tool(toolgroup:str, tool:str, request: Request, run: bool=False):

    toolgroup_config = web_config.get('groups', {}).get(toolgroup, None)
    if not toolgroup_config:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "error_message": f"Toolgroup '{toolgroup}' not found.",
            "web_config": web_config
        }, status_code=404)

    tool_config = toolgroup_config.get('tools', {}).get(tool, None)
    if not tool_config:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "error_message": f"Tool '{tool}' not found in toolgroup '{toolgroup}'.",
            "web_config": web_config
        }, status_code=404)

    toolbox_module = tb.load_module(tool_config.get('module'))
    toolbox_arguments = toolbox_module.Arguments.model_fields

    get_params = {}
    output_str = ""
    if run:
        get_params = dict(request.query_params)
        output_data = toolbox_wrapper(toolbox_module, **get_params)


        if toolbox_module.OUTPUT_HTML_JINJA2:
            output_template = Template(toolbox_module.OUTPUT_HTML_JINJA2)
            output_str = output_template.render(data=output_data)
        else:
            output_str = "No Output defined in Module"


    return templates.TemplateResponse("tool.html", {
        "request": request,
        "web_config": web_config,
        "path": (toolgroup, tool),
        "toolbox_arguments": toolbox_arguments,
        "toolgroup_config": toolgroup_config,
        "tool_config": tool_config,
        "toolbox_module": toolbox_module,
        "run": run,
        "params": get_params,
        "output_str": output_str
    })



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
