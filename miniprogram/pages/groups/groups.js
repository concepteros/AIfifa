const { worldCupData } = require("../../utils/worldcup-data");
const { buildGroupSchedule, groupTeams, percent, teamLabel } = require("../../utils/helpers");

function decorateTeam(team) {
  return {
    ...team,
    label: teamLabel(team),
    probabilityText: percent(team.probability)
  };
}

Page({
  data: {
    groups: [],
    schedule: []
  },

  onLoad() {
    const groupMap = groupTeams(worldCupData.teams);
    const groups = Object.keys(groupMap).sort().map((group) => ({
      group,
      teams: groupMap[group].map(decorateTeam)
    }));
    const schedule = buildGroupSchedule(worldCupData.teams).map((match, index) => ({
      ...match,
      id: `${match.group}-${match.label}-${index}`,
      homeLabel: teamLabel(match.home),
      awayLabel: teamLabel(match.away),
      score: match.score || "Waiting"
    }));
    this.setData({ groups, schedule });
  },

  openTeam(event) {
    const { code } = event.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/team/team?code=${code}` });
  }
});
