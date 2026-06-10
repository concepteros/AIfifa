function teamLabel(team) {
  if (!team) return "TBD";
  return `${team.flagEmoji || ""} ${team.name}`.trim();
}

function percent(value) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function groupTeams(teams) {
  return teams.reduce((result, team) => {
    if (!result[team.group]) result[team.group] = [];
    result[team.group].push(team);
    return result;
  }, {});
}

const GROUP_SCHEDULE_META = {
  1: {
    A: { date: "2026-06-12", time: "03:00", venues: ["Estadio Azteca, Mexico City", "Estadio Guadalajara"] },
    B: { date: "2026-06-13", time: "06:00", venues: ["BMO Field, Toronto", "BC Place, Vancouver"] },
    C: { date: "2026-06-14", time: "03:00", venues: ["Hard Rock Stadium, Miami", "Mercedes-Benz Stadium, Atlanta"] },
    D: { date: "2026-06-13", time: "10:00", venues: ["SoFi Stadium, Los Angeles", "Levi's Stadium, San Francisco Bay Area"] },
    E: { date: "2026-06-15", time: "03:00", venues: ["AT&T Stadium, Dallas", "NRG Stadium, Houston"] },
    F: { date: "2026-06-15", time: "06:00", venues: ["Lumen Field, Seattle", "BC Place, Vancouver"] },
    G: { date: "2026-06-16", time: "03:00", venues: ["MetLife Stadium, New York New Jersey", "Lincoln Financial Field, Philadelphia"] },
    H: { date: "2026-06-16", time: "06:00", venues: ["Gillette Stadium, Boston", "Hard Rock Stadium, Miami"] },
    I: { date: "2026-06-17", time: "03:00", venues: ["Arrowhead Stadium, Kansas City", "AT&T Stadium, Dallas"] },
    J: { date: "2026-06-17", time: "06:00", venues: ["Mercedes-Benz Stadium, Atlanta", "NRG Stadium, Houston"] },
    K: { date: "2026-06-18", time: "03:00", venues: ["Estadio Monterrey", "Estadio Guadalajara"] },
    L: { date: "2026-06-18", time: "06:00", venues: ["SoFi Stadium, Los Angeles", "Levi's Stadium, San Francisco Bay Area"] }
  },
  2: {
    A: { date: "2026-06-19", time: "03:00", venues: ["Estadio Azteca, Mexico City", "Estadio Monterrey"] },
    B: { date: "2026-06-19", time: "06:00", venues: ["BMO Field, Toronto", "BC Place, Vancouver"] },
    C: { date: "2026-06-20", time: "03:00", venues: ["Hard Rock Stadium, Miami", "Mercedes-Benz Stadium, Atlanta"] },
    D: { date: "2026-06-20", time: "06:00", venues: ["SoFi Stadium, Los Angeles", "Lumen Field, Seattle"] },
    E: { date: "2026-06-21", time: "03:00", venues: ["AT&T Stadium, Dallas", "NRG Stadium, Houston"] },
    F: { date: "2026-06-21", time: "06:00", venues: ["Levi's Stadium, San Francisco Bay Area", "BC Place, Vancouver"] },
    G: { date: "2026-06-22", time: "03:00", venues: ["MetLife Stadium, New York New Jersey", "Lincoln Financial Field, Philadelphia"] },
    H: { date: "2026-06-22", time: "06:00", venues: ["Gillette Stadium, Boston", "Hard Rock Stadium, Miami"] },
    I: { date: "2026-06-23", time: "03:00", venues: ["Arrowhead Stadium, Kansas City", "AT&T Stadium, Dallas"] },
    J: { date: "2026-06-23", time: "06:00", venues: ["Mercedes-Benz Stadium, Atlanta", "NRG Stadium, Houston"] },
    K: { date: "2026-06-24", time: "03:00", venues: ["Estadio Monterrey", "Estadio Guadalajara"] },
    L: { date: "2026-06-24", time: "06:00", venues: ["SoFi Stadium, Los Angeles", "Levi's Stadium, San Francisco Bay Area"] }
  },
  3: {
    A: { date: "2026-06-25", time: "03:00", venues: ["Estadio Azteca, Mexico City", "Estadio Guadalajara"] },
    B: { date: "2026-06-25", time: "06:00", venues: ["BMO Field, Toronto", "BC Place, Vancouver"] },
    C: { date: "2026-06-25", time: "10:00", venues: ["Hard Rock Stadium, Miami", "Mercedes-Benz Stadium, Atlanta"] },
    D: { date: "2026-06-26", time: "03:00", venues: ["SoFi Stadium, Los Angeles", "Lumen Field, Seattle"] },
    E: { date: "2026-06-26", time: "06:00", venues: ["AT&T Stadium, Dallas", "NRG Stadium, Houston"] },
    F: { date: "2026-06-26", time: "10:00", venues: ["Levi's Stadium, San Francisco Bay Area", "BC Place, Vancouver"] },
    G: { date: "2026-06-27", time: "03:00", venues: ["MetLife Stadium, New York New Jersey", "Lincoln Financial Field, Philadelphia"] },
    H: { date: "2026-06-27", time: "06:00", venues: ["Gillette Stadium, Boston", "Hard Rock Stadium, Miami"] },
    I: { date: "2026-06-27", time: "10:00", venues: ["Arrowhead Stadium, Kansas City", "AT&T Stadium, Dallas"] },
    J: { date: "2026-06-28", time: "03:00", venues: ["Mercedes-Benz Stadium, Atlanta", "NRG Stadium, Houston"] },
    K: { date: "2026-06-28", time: "06:00", venues: ["Estadio Monterrey", "Estadio Guadalajara"] },
    L: { date: "2026-06-28", time: "10:00", venues: ["SoFi Stadium, Los Angeles", "Levi's Stadium, San Francisco Bay Area"] }
  }
};

function buildGroupSchedule(teams) {
  const groups = groupTeams(teams);
  const rounds = [
    { matchday: 1, label: "第 1 轮", pairs: [[0, 1], [2, 3]] },
    { matchday: 2, label: "第 2 轮", pairs: [[0, 2], [3, 1]] },
    { matchday: 3, label: "第 3 轮", pairs: [[3, 0], [1, 2]] }
  ];
  const matches = [];
  rounds.forEach((round) => {
    Object.keys(groups).sort().forEach((group) => {
      round.pairs.forEach(([homeIndex, awayIndex], pairIndex) => {
        const meta = GROUP_SCHEDULE_META[round.matchday][group] || {};
        matches.push({
          date: meta.date || "TBD",
          time: meta.time || "TBD",
          bjt: `${meta.date || "TBD"} ${meta.time || "TBD"} BJT`,
          label: round.label,
          group,
          venue: meta.venues && meta.venues[pairIndex] ? meta.venues[pairIndex] : "Venue TBD",
          score: "Waiting",
          home: groups[group][homeIndex],
          away: groups[group][awayIndex]
        });
      });
    });
  });
  return matches;
}

module.exports = {
  buildGroupSchedule,
  groupTeams,
  percent,
  teamLabel
};
