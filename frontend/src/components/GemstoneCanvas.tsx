import React, { useEffect, useRef } from 'react';
import * as THREE from 'three'; // Use namespace import for Three.js
import '../components/styles/starry-background.css';

const GemstoneCanvas: React.FC = () => {
  const mountRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const gemMeshRef = useRef<THREE.Mesh | null>(null);
  const clockRef = useRef(new THREE.Clock());
  const animationFrameIdRef = useRef<number | null>(null);
  const envMapTextureRef = useRef<THREE.CubeTexture | null>(null);

  useEffect(() => {
    if (!mountRef.current || rendererRef.current) return; 

    let camera: THREE.PerspectiveCamera;
    let scene: THREE.Scene;
    let renderer: THREE.WebGLRenderer;
    let gemMesh: THREE.Mesh;

    const threeJsContainer = mountRef.current;

    function createGeometryWithFacets(radius = 1, detail = 4) {
      // Create a more crystalline, gemstone-like geometry with facets
      const geometry = new THREE.IcosahedronGeometry(radius, detail);
      // Add randomization to vertices to create more interesting facets
      const positions = geometry.attributes.position;
      const vertex = new THREE.Vector3();
      const normal = new THREE.Vector3();
      
      for (let i = 0; i < positions.count; i++) {
        vertex.fromBufferAttribute(positions, i);
        normal.copy(vertex).normalize();
        
        // Create faceted look with controlled randomization
        const noise = Math.sin(vertex.x * 5) * Math.cos(vertex.y * 6) * Math.sin(vertex.z * 4) * 0.03;
        vertex.addScaledVector(normal, noise);
        
        positions.setXYZ(i, vertex.x, vertex.y, vertex.z);
      }
      
      // Compute new normals to ensure proper lighting on facets
      geometry.computeVertexNormals();
      return geometry;
    }

    function init() {
      const containerWidth = threeJsContainer.clientWidth;
      const containerHeight = Math.max(threeJsContainer.clientHeight, 300); // Min height for canvas

      camera = new THREE.PerspectiveCamera(30, containerWidth / containerHeight, 0.1, 100); // Narrower FOV for more dramatic look
      camera.position.set(0, 0, 5.0); // Positioned straight on
      cameraRef.current = camera;

      scene = new THREE.Scene();
      scene.background = null; // Transparent background
      sceneRef.current = scene;

      // Enhanced lighting setup for more dramatic gem appearance
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.15); 
      scene.add(ambientLight);

      // Pink/purple accent lights that match the UI theme
      const pointLight1 = new THREE.PointLight(0xec4899, 45, 12, 1.5); // Pink-500
      pointLight1.position.set(3, 2, 3);
      scene.add(pointLight1);
      
      const pointLight2 = new THREE.PointLight(0xa78bfa, 40, 12, 1.5); // Purple-400
      pointLight2.position.set(-3, -2, 3);
      scene.add(pointLight2);

      // Rim light for highlights
      const pointLight3 = new THREE.PointLight(0xffffff, 20, 15, 1.2);
      pointLight3.position.set(0, 3, -5);
      scene.add(pointLight3);

      // Environment map for reflections
      try {
        const cubeTextureLoader = new THREE.CubeTextureLoader();
        cubeTextureLoader.setPath('https://threejs.org/examples/textures/cube/MilkyWay/'); // Starry environment map
        envMapTextureRef.current = cubeTextureLoader.load(['dark-s_px.jpg', 'dark-s_nx.jpg', 'dark-s_py.jpg', 'dark-s_ny.jpg', 'dark-s_pz.jpg', 'dark-s_nz.jpg']);
        envMapTextureRef.current.colorSpace = THREE.SRGBColorSpace;
      } catch (e) {
        console.warn("Could not load CubeTexture for environment map.", e);
        envMapTextureRef.current = null;
      }

      // Create a more faceted gemstone geometry
      const geometry = createGeometryWithFacets(1, 5);

      // Enhanced material with pink/purple tint and higher clarity
      const material = new THREE.MeshPhysicalMaterial({
        color: 0xf5e6ff, // Very light purple base
        metalness: 0.05,    // Lower metalness for crystal appearance
        roughness: 0.01,    // Very low roughness for high gloss
        transmission: 0.92, // High transmission for transparency
        ior: 2.4,          // Higher index of refraction for stronger light bending
        thickness: 0.5,    
        envMap: envMapTextureRef.current, 
        envMapIntensity: 1.8, 
        specularIntensity: 1.2,
        specularColor: 0xffffff, 
        transparent: true,
        opacity: 0.9,      
        attenuationColor: 0xec4899, // Pink tint to transmitted light
        attenuationDistance: 2.0,
        clearcoat: 0.3,     // Slight clearcoat for extra shine
        clearcoatRoughness: 0.1,
        depthWrite: true,
      });

      gemMesh = new THREE.Mesh(geometry, material);
      gemMesh.scale.set(1.2, 1.2, 1.2); // Slightly larger to be more prominent
      scene.add(gemMesh);
      gemMeshRef.current = gemMesh;

      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); 
      renderer.setPixelRatio(window.devicePixelRatio);
      renderer.setSize(containerWidth, containerHeight);
      renderer.toneMapping = THREE.ACESFilmicToneMapping; 
      renderer.toneMappingExposure = 1.3; 
      rendererRef.current = renderer;
      
      threeJsContainer.appendChild(renderer.domElement);
      
      window.addEventListener('resize', onWindowResize);
      animate();
    }

    function onWindowResize() {
      if (!threeJsContainer || !cameraRef.current || !rendererRef.current) return;
      const containerWidth = threeJsContainer.clientWidth;
      const containerHeight = Math.max(threeJsContainer.clientHeight, 250);

      cameraRef.current.aspect = containerWidth / containerHeight;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(containerWidth, containerHeight);
    }

    function animate() {
      animationFrameIdRef.current = requestAnimationFrame(animate);
      const elapsedTime = clockRef.current.getElapsedTime();

      if (gemMeshRef.current) {
        gemMeshRef.current.rotation.x = Math.sin(elapsedTime * 0.1) * 0.08; 
        gemMeshRef.current.rotation.y += 0.0015; 
        gemMeshRef.current.rotation.z = Math.cos(elapsedTime * 0.08) * 0.06;  
        gemMeshRef.current.position.y = Math.sin(elapsedTime * 0.3) * 0.04; 
      }
      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current);
      }
    }

    init();

    return () => {
      window.removeEventListener('resize', onWindowResize);
      if (animationFrameIdRef.current) {
        cancelAnimationFrame(animationFrameIdRef.current);
      }
      
      if (sceneRef.current) {
        sceneRef.current.traverse(object => {
            if (object instanceof THREE.Mesh) {
                if (object.geometry) object.geometry.dispose();
                if (object.material) {
                    const mat = object.material as THREE.Material | THREE.Material[];
                    if (Array.isArray(mat)) {
                        mat.forEach(m => { if (m.dispose) m.dispose(); });
                    } else {
                        if (mat.dispose) mat.dispose();
                    }
                }
            }
        });
      }
      if (envMapTextureRef.current) {
        envMapTextureRef.current.dispose();
        envMapTextureRef.current = null;
      }
      if (rendererRef.current) {
        rendererRef.current.dispose();
        if (rendererRef.current.domElement && rendererRef.current.domElement.parentNode) {
           rendererRef.current.domElement.parentNode.removeChild(rendererRef.current.domElement);
        }
        rendererRef.current = null; 
      }
      sceneRef.current = null;
      cameraRef.current = null;
      gemMeshRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); 

  return <div id="threejs-gem-canvas" ref={mountRef} className="w-full h-full touch-none" aria-label="Animated 3D gemstone visualization"></div>;
};

export default GemstoneCanvas;
