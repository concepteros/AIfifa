const { worldCupData, squads } = require("../../utils/worldcup-data");
const { percent, teamLabel } = require("../../utils/helpers");

const COACHES = {
  ARG: "Lionel Scaloni",
  BRA: "Carlo Ancelotti",
  ENG: "Thomas Tuchel",
  ESP: "Luis de la Fuente",
  FRA: "Didier Deschamps",
  GER: "Julian Nagelsmann",
  JPN: "Hajime Moriyasu",
  MEX: "Javier Aguirre",
  NED: "Ronald Koeman",
  POR: "Roberto Martinez",
  USA: "Mauricio Pochettino"
};

function valueText(value) {
  return value === undefined || value === null || value === "" ? "-" : String(value);
}

Page({
  data: {
    team: {},
    coach: "官方信息待更新",
    players: []
  },

  onLoad(query) {
    const code = query.code;
    const team = worldCupData.teams.find((item) => item.code === code) || worldCupData.teams[0];
    const rawPlayers = squads[team.code] || team.players || [];
    const players = rawPlayers.map((player) => ({
      ...player,
      ageText: valueText(player.age),
      capsText: valueText(player.caps),
      goalsText: valueText(player.goals),
      club: valueText(player.club)
    }));

    this.setData({
      team: {
        ...team,
        label: teamLabel(team),
        probabilityText: percent(team.probability)
      },
      coach: COACHES[team.code] || "官方信息待更新",
      players
    });
    wx.setNavigationBarTitle({ title: team.name });
  }
});
