const script = document.createElement('script');
script.src = "https://cdnjs.cloudflare.com/ajax/libs/two.js/0.8.12/two.min.js";
  script.onload = () => {
    const two = new Two({ width: 500, height: 500 }).appendTo(el);

    // Draw a rectangle
    const rect = two.makeRectangle(250, 250, 100, 100);
    rect.fill = '#FF0000';
    rect.stroke = '#000000';
    rect.linewidth = 5;

    two.update();
  };