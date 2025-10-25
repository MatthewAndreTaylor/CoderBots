import anywidget
import traitlets

class RobotPanel(anywidget.AnyWidget):
    _esm = """
    export async function render({ model, el }) {
        el.innerHTML = "";

        await new Promise((resolve) => {
            if (window.Two) {
                resolve();
                return;
            }
            const script = document.createElement('script');
            script.src = "https://cdnjs.cloudflare.com/ajax/libs/two.js/0.8.12/two.min.js";
            script.onload = resolve;
            document.head.appendChild(script);
        });

        const title = document.createElement('h3');
        title.textContent = model.get("title");
        el.appendChild(title);

        // Canvas container with border
        const canvasContainer = document.createElement("div");
        canvasContainer.style.border = "2px solid #444";
        canvasContainer.style.borderRadius = "8px";
        canvasContainer.style.boxShadow = "0 2px 6px rgba(0,0,0,0.1)";
        canvasContainer.style.display = "flex";
        canvasContainer.style.alignItems = "center";
        canvasContainer.style.justifyContent = "center";
        el.appendChild(canvasContainer);
        const two = new Two({ width: 800, height: 600 }).appendTo(canvasContainer);
        const rect = two.makeRectangle(250, 250, 25, 25);
        rect.fill = '#FF0000';
        rect.stroke = '#000';
        rect.linewidth = 4;
        two.update();

        el.style.display = "flex";
        el.style.flexDirection = "column";
        el.style.alignItems = "center";
        el.style.gap = "1em";
    }
    """

    title = traitlets.Unicode("Robot Control Panel").tag(sync=True)
