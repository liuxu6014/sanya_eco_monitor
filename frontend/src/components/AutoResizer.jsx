import React, { useState, useEffect, useRef } from 'react';

/**
 * AutoResizer: A component that scales its children to fit the container
 * while maintaining a fixed design aspect ratio (e.g. 1920x1080).
 */
export default function AutoResizer({ children, designHeight = 1080 }) {
  const [state, setState] = useState({ scale: 1, width: 1920 });
  const wrapperRef = useRef(null);

  useEffect(() => {
    const handleResize = () => {
      const wh = window.innerHeight;
      const ww = window.innerWidth;
      
      // Calculate scale based on height to ensure vertical content fits
      const scale = wh / designHeight;
      
      // Calculate required internal width to fill the screen width at this scale
      const fluidWidth = ww / scale;
      
      setState({ scale, width: fluidWidth });
    };

    window.addEventListener('resize', handleResize);
    handleResize();
    
    return () => window.removeEventListener('resize', handleResize);
  }, [designHeight]);

  return (
    <div 
      style={{ 
        width: '100vw', 
        height: '100vh', 
        overflow: 'hidden', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        background: '#020611'
      }}
    >
      <div
        ref={wrapperRef}
        style={{
          width: `${state.width}px`,
          height: `${designHeight}px`,
          transform: `scale(${state.scale})`,
          transformOrigin: 'center center',
          flexShrink: 0,
          transition: 'transform 0.1s ease-out',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {children}
      </div>
    </div>
  );
}
