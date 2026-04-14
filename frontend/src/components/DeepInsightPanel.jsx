import React, { useState, useEffect } from 'react'
import ReactECharts from 'echarts-for-react'

export default function DeepInsightPanel({ ecoIndex }) {
  const d = ecoIndex?.data || {}
  const [showInsights, setShowInsights] = useState(false)
  
  useEffect(() => {
     setShowInsights(false)
     const t = setTimeout(() => setShowInsights(true), 600)
     return () => clearTimeout(t)
  }, [d.eco_health])
  
  const radarOption = {
    backgroundColor: 'transparent',
    radar: {
      indicator: [
        { name: '流失控制', max: 100 },
        { name: '生境适宜', max: 100 },
        { name: '植保防御', max: 100 },
        { name: '面源环境', max: 100 },
        { name: '水文健康', max: 100 }
      ],
      shape: 'polygon',
      radius: '65%',
      splitNumber: 6,
      axisName: { color: '#a5b4fc', fontSize: 11, fontWeight: 'bold', textShadow: '0 0 5px #6366f1' },
      splitLine: { 
        lineStyle: { 
          color: ['rgba(99, 102, 241, 0.1)', 'rgba(99, 102, 241, 0.2)', 'rgba(99, 102, 241, 0.4)', 'rgba(99, 102, 241, 0.6)', 'rgba(99, 102, 241, 0.8)', 'rgba(99, 102, 241, 1)']
        } 
      },
      splitArea: { 
        show: true,
        areaStyle: { color: ['rgba(0,0,0,0)', 'rgba(99, 102, 241, 0.05)'] }
      },
      axisLine: { lineStyle: { color: 'rgba(99, 102, 241, 0.5)', type: 'dashed' } }
    },
    series: [
      {
        type: 'radar',
        data: [{
          value: [
            Math.min(100, Math.max(0, 100 - (d.erosion_risk || 0))),
            d.growth_suitability || 0,
            Math.min(100, Math.max(0, 100 - (d.pest_risk || 0))),
            Math.min(100, Math.max(0, 100 - (d.pollution_load || 0))),
            Math.min(100, Math.max(0, 100 - (d.irrigation_urgency || 0)))
          ],
          name: 'Realtime Data',
          symbol: 'circle',
          symbolSize: 6,
          itemStyle: { color: '#818cf8', borderColor: '#fff', borderWidth: 2, shadowColor: '#818cf8', shadowBlur: 10 },
          areaStyle: { 
            color: {
              type: 'radial', x: 0.5, y: 0.5, r: 0.5,
              colorStops: [{ offset: 0, color: 'rgba(99, 102, 241, 0.6)' }, { offset: 1, color: 'rgba(168, 85, 247, 0.2)' }]
            }
          },
          lineStyle: { width: 3, color: '#818cf8', shadowBlur: 15, shadowColor: '#818cf8' }
        },
        {
          value: [90, 85, 95, 88, 92],
          name: 'Ideal State',
          symbol: 'none',
          lineStyle: { width: 2, type: 'dotted', color: 'rgba(56, 189, 248, 0.8)' },
          areaStyle: { color: 'rgba(56, 189, 248, 0.0)' }
        }]
      }
    ]
  }

  return (
    <div style={{ 
        display: 'flex', gap: '20px', height: '100%', padding: '10px 15px',
        color: '#e2e8f0', fontFamily: 'monospace', position: 'relative',
        overflow: 'hidden', background: 'radial-gradient(circle at center, rgba(30, 41, 59, 0.6) 0%, rgba(2, 6, 23, 0.9) 100%)',
        backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px)',
        backgroundSize: '20px 20px'
    }}>
      
      {/* LEFT: Dynamic Heartbeat Radar */}
      <div style={{ flex: '1', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'relative', background: 'url("data:image/svg+xml,%3Csvg width=\'200\' height=\'200\' viewBox=\'0 0 200 200\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Ccircle cx=\'100\' cy=\'100\' r=\'90\' fill=\'none\' stroke=\'rgba(99,102,241,0.05)\' stroke-width=\'40\' stroke-dasharray=\'2 6\'/%3E%3C/svg%3E") center center no-repeat' }}>
          
          <div style={{ position: 'absolute', width: '280px', height: '280px', borderRadius: '50%', border: '1px dashed rgba(99,102,241,0.3)', animation: 'spin 60s linear infinite' }} />
          <div style={{ position: 'absolute', width: '240px', height: '240px', borderRadius: '50%', border: '1px solid rgba(56,189,248,0.1)', animation: 'spin 40s reverse linear infinite' }} />

          <div style={{ width: '100%', height: '320px', zIndex: 10 }}>
              <ReactECharts option={radarOption} style={{ height: '100%', width: '100%' }} />
          </div>

          <div style={{ position: 'absolute', bottom: '0px', textAlign: 'center', padding: '10px', background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.4)', borderRadius: '8px', backdropFilter: 'blur(4px)', boxShadow: '0 4px 15px rgba(0,0,0,0.5)' }}>
              <div style={{ fontSize: '10px', color: '#a5b4fc', fontWeight: 'bold', letterSpacing: '1px' }}>SYS.ECO_INTEGRITY</div>
              <div style={{ fontSize: '42px', fontWeight: '900', color: '#fff', textShadow: '0 0 20px rgba(99, 102, 241, 0.8)', lineHeight: '1' }}>
                  {d.eco_health || '--'}<span style={{ fontSize: '18px', color: '#6366f1' }}>/100</span>
              </div>
          </div>
      </div>

      {/* RIGHT: Technical Grid Indicators */}
      <div style={{ flex: '2', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', flex: 1.5 }}>
             <SensorHudCard 
                label="水土流失风险" value={d.erosion_risk} 
                theme="#38bdf8"
             />
             <SensorHudCard 
                label="水环境污染负荷" value={d.pollution_load} 
                theme="#fbbf24"
             />
             <SensorHudCard 
                label="病虫爆发预警" value={d.pest_risk} 
                theme="#f472b6"
             />
             <SensorHudCard 
                label="植被生长适宜度" value={d.growth_suitability} 
                theme="#4ade80"
             />
          </div>

          {/* AI Smart Insight Box */}
          <div style={{ 
              flex: 1, background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(15, 23, 42, 0.8))', 
              border: '1px solid rgba(99, 102, 241, 0.3)', 
              borderRadius: '12px', padding: '16px 20px', position: 'relative', overflow: 'hidden',
              boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
              display: 'flex', gap: '24px', alignItems: 'center'
          }}>
             {/* Beautiful stylized decoration */}
             <div style={{ flex: '0 0 80px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
                <div style={{ width: '60px', height: '60px', borderRadius: '30px', background: 'rgba(99, 102, 241, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(99, 102, 241, 0.5)', boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)' }}>
                   <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                       <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" style={{ animation: 'spin 15s linear infinite', transformOrigin: 'center' }}/>
                       <circle cx="12" cy="12" r="4" fill="#6366f1" />
                   </svg>
                </div>
                <div style={{ fontSize: '11px', color: '#818cf8', fontWeight: 'bold', marginTop: '10px', letterSpacing: '2px' }}>AI CORE</div>
             </div>

             {/* Insights Content */}
             <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '10px', opacity: showInsights ? 1 : 0, transform: showInsights ? 'translateY(0)' : 'translateY(10px)', transition: 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)' }}>
                <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#f8fafc', textShadow: '0 0 5px rgba(255,255,255,0.3)', letterSpacing: '1px' }}>
                    生态综合评估：{d.eco_health > 80 ? '系统健康度高，状态稳定' : '存在局部环境扰动风险'}
                </div>
                
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                    <div style={{ width: '4px', height: '14px', borderRadius: '4px', background: '#38bdf8', marginTop: '4px', boxShadow: '0 0 8px #38bdf8' }} />
                    <div style={{ fontSize: '13px', color: '#cbd5e1', lineHeight: '1.6' }}>
                        {d.erosion_risk > 50 ? "水土预警：检测到局部水土流失风险增加，建议采取坡面护坡保土措施。" : "水土状态：24小时内未见异常土壤侵蚀，地表径流系统运行平稳。"}
                    </div>
                </div>
                
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                    <div style={{ width: '4px', height: '14px', borderRadius: '4px', background: '#4ade80', marginTop: '4px', boxShadow: '0 0 8px #4ade80' }} />
                    <div style={{ fontSize: '13px', color: '#cbd5e1', lineHeight: '1.6' }}>
                        植被监测：当前区域的温湿度与土壤养分综合配比，非常适合本地农林作物的自然生长。
                    </div>
                </div>
             </div>
             
             {/* Decorative watermark */}
             <div style={{ position: 'absolute', bottom: '-8px', right: '15px', fontSize: '64px', fontWeight: '900', color: 'rgba(99, 102, 241, 0.04)', letterSpacing: '-2px', fontStyle: 'italic', pointerEvents: 'none' }}>
                SUMMARY
             </div>
          </div>
      </div>

      <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
      `}</style>
    </div>
  )
}

function SensorHudCard({ label, value, theme }) {
    const safeValue = typeof value === 'number' && !isNaN(value) ? value : 0;
    const isCritical = safeValue > 70 || (theme === '#f472b6' && safeValue > 50);

    return (
        <div style={{ 
            background: 'linear-gradient(145deg, rgba(15, 23, 42, 0.7) 0%, rgba(2, 6, 23, 0.9) 100%)', 
            border: `1px solid ${isCritical ? theme : 'rgba(255,255,255,0.05)'}`, 
            borderTop: `1px solid rgba(255,255,255,0.1)`,
            borderRadius: '12px', padding: '14px 20px', display: 'flex', gap: '20px', position: 'relative',
            overflow: 'hidden', 
            boxShadow: isCritical ? `0 0 25px ${theme}33, inset 0 0 20px ${theme}11` : '0 8px 16px rgba(0,0,0,0.6)',
            transition: 'all 0.3s ease-in-out',
            alignItems: 'center',
            backdropFilter: 'blur(10px)'
        }}>
            {/* Multi-layered Background Glow */}
            <div style={{ position: 'absolute', top: '0', left: '0', width: '4px', height: '100%', background: theme, boxShadow: `0 0 15px ${theme}` }} />
            <div style={{ position: 'absolute', top: '10%', left: '-10%', width: '100px', height: '100px', background: theme, filter: 'blur(45px)', opacity: 0.2 }} />

            {/* Circular Premium Gauge */}
            <div style={{ flex: '0 0 60px', height: '60px', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <svg width="60" height="60" viewBox="0 0 100 100" style={{ transform: 'rotate(-90deg)', position: 'absolute', dropShadow: `0 0 5px ${theme}` }}>
                    <circle cx="50" cy="50" r="44" fill="rgba(0,0,0,0.2)" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
                    <circle cx="50" cy="50" r="44" fill="none" stroke={theme} strokeWidth="8" strokeDasharray={2 * Math.PI * 44} strokeDashoffset={2 * Math.PI * 44 * (1 - safeValue / 100)} strokeLinecap="round" style={{ transition: 'stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1)' }} />
                </svg>
                {/* Embedded Glowing Metric */}
                <div style={{ 
                    position: 'relative', display: 'flex', alignItems: 'baseline',
                    color: '#fff', textShadow: `0 0 10px ${theme}, 0 0 20px ${theme}`, fontFamily: 'monospace'
                }}>
                    <span style={{ fontSize: '20px', fontWeight: '900', fontStyle: 'italic', lineHeight: '1' }}>{safeValue}</span>
                </div>
            </div>

            {/* Core Info Area */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '6px' }}>
                <div style={{ 
                    fontSize: '16px', fontWeight: 'bold', letterSpacing: '2px', 
                    background: `linear-gradient(90deg, #fff, ${theme})`, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                    textShadow: '0 2px 4px rgba(0,0,0,0.4)', alignSelf: 'flex-start'
                }}>
                    {label}
                </div>
                
                {/* Tech Progress Bar */}
                <div style={{ width: '100%', height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px', position: 'relative', overflow: 'hidden' }}>
                    <div style={{ 
                        position: 'absolute', top: 0, left: 0, height: '100%', width: `${safeValue}%`, 
                        background: `linear-gradient(90deg, transparent, ${theme})`,
                        boxShadow: `0 0 8px ${theme}`, transition: 'width 1.5s ease-out'
                    }} />
                </div>
            </div>

            {/* Elegant Status Badge */}
            <div style={{ 
                display: 'flex', alignItems: 'center', gap: '6px', 
                padding: '4px 10px', borderRadius: '20px', 
                background: isCritical ? `${theme}22` : 'rgba(255,255,255,0.03)',
                border: `1px solid ${isCritical ? theme : 'rgba(255,255,255,0.1)'}`,
                boxShadow: isCritical ? `0 0 10px ${theme}40` : 'none'
            }}>
                {isCritical && <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: theme, boxShadow: `0 0 8px ${theme}`, animation: 'blink 1s infinite' }} />}
                <div style={{ fontSize: '10px', color: isCritical ? theme : '#94a3b8', fontWeight: '900', letterSpacing: '1px' }}>
                    {isCritical ? 'ALERT' : 'NORM'}
                </div>
            </div>
        </div>
    )
}
