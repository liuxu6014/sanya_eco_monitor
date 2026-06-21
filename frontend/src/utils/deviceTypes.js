// 设备数据类型的统一标签与配色（设备运维板块共用）。
export const TYPE_LABELS = {
  insect: '虫情',
  spore: '孢子',
  water: '水质',
  runoff: '径流',
  rain: '雨量',
}

export const TYPE_COLORS = {
  insect: '#fbbf24',
  spore: '#c084fc',
  water: '#22d3ee',
  runoff: '#60a5fa',
  rain: '#2dd4bf',
}

// 虫情、孢子约一天一报，仅识别"连续多日掉线"，时长以"天"显示更直观。
export const LOW_FREQ_TYPES = new Set(['insect', 'spore'])

export function deviceLabel(name, type) {
  const tag = TYPE_LABELS[type]
  return tag ? `${name}（${tag}）` : name
}
