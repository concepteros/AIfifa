const { worldCupData } = require("../../utils/worldcup-data");
const { percent, teamLabel } = require("../../utils/helpers");

function decorateTeam(team) {
  return {
    ...team,
    label: teamLabel(team),
    probabilityText: percent(team.probability)
  };
}

Page({
  data: {
    teams: [],
    topTeams: [],
    updatedAt: ""
  },

  onLoad() {
    this.loadData();
  },

  loadData() {
    const teams = [...worldCupData.teams]
      .sort((a, b) => a.group.localeCompare(b.group) || b.probability - a.probability)
      .map(decorateTeam);
    const topTeams = [...worldCupData.teams]
      .sort((a, b) => b.probability - a.probability)
      .slice(0, 12)
      .map(decorateTeam);

    this.setData({
      teams,
      topTeams,
      updatedAt: "本地数据"
    });
  },

  refreshLocal() {
    this.setData({ updatedAt: "刚刚更新" });
    wx.showToast({ title: "已刷新", icon: "success" });
  },

  openTeam(event) {
    const { code } = event.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/team/team?code=${code}` });
  }
});
