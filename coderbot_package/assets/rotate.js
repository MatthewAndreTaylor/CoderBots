window.addEventListener('DOMContentLoaded', () => {
  const turretElement = document.getElementById('turret');

  if (turretElement) {

    function setRotation(el, degrees) {
      // Keep existing translate() part
      const transform = el.getAttribute('transform') || '';
      const translateMatch = transform.match(/translate\([^)]*\)/);
      const translatePart = translateMatch ? translateMatch[0] : 'translate(88,70)'; // fallback

      // Rotate around (0,0)
      const rotation = `rotate(${degrees})`;
      const newTransform = `${translatePart} ${rotation}`;
      el.setAttribute('transform', newTransform);
    }

    function rotateBy(el, delta) {
      const transform = el.getAttribute('transform') || '';
      const match = transform.match(/rotate\(\s*([-\d.]+)/);
          const current = match ? parseFloat(match[1]) : 0;
      const next = current + delta;
      setRotation(el, next);
    }

    function incrementTurretRotation() {
      rotateBy(turretElement, 10);
    }

    const rotateButton = document.getElementById('rotateButton');
    if (rotateButton) {
      rotateButton.addEventListener('click', incrementTurretRotation);
    } else {
      console.warn("Button with ID 'rotateButton' not found.");
    }

  } else {
    console.error("SVG element with ID 'turret' not found.");
  }
});