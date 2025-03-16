# nix develop | pull dependencies
# dune init project <projectname>
# change packageName on line 15 with <projectname>
{
  description = "nix flake to build ocaml dune projects";

  inputs = {
    systems.url = "github:nix-systems/default";
  };

  outputs = { self, nixpkgs, systems }:
    let
      lib = nixpkgs.lib;
      eachSystem = lib.genAttrs (import systems);
      packageName = "hello";
    in
    {
      packages = eachSystem (system:
        let
          legacyPackages = nixpkgs.legacyPackages.${system};
          ocamlPackages = legacyPackages.ocamlPackages;
        in
        {
          default = self.packages.${system}.ocamlProject;

          ocamlProject = ocamlPackages.buildDunePackage {
            pname = packageName;
            version = "0.1.0";
            duneVersion = "3";
            src = ./.;

            buildInputs = [
              # OCaml package dependencies go here.
            ];

            strictDeps = true;
          };
        });

      devShells = eachSystem (system:
        let
          legacyPackages = nixpkgs.legacyPackages.${system};
          ocamlPackages = legacyPackages.ocamlPackages;
        in
        {
          default = legacyPackages.mkShell {
            packages = [
              legacyPackages.fswatch
              ocamlPackages.odoc
              ocamlPackages.ocaml-lsp
              ocamlPackages.utop
            ];

            inputsFrom = [
              self.packages.${system}.ocamlProject
            ];
          };
        });
    };
}
